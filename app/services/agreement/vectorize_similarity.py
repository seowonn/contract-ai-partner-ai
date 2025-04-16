import asyncio
import logging
import time
from asyncio import Semaphore
from typing import List, Optional, Any

import fitz
from openai import AsyncAzureOpenAI
import numpy as np
from qdrant_client import models, AsyncQdrantClient
from qdrant_client.http.models import QueryResponse

from app.blueprints.agreement.agreement_exception import AgreementException
from app.clients.openai_clients import get_prompt_async_client, \
  get_embedding_async_client
from app.clients.qdrant_client import get_qdrant_client
from app.common.chunk_status import ChunkProcessResult, ChunkProcessStatus
from app.common.constants import ARTICLE_CLAUSE_SEPARATOR, \
  CLAUSE_TEXT_SEPARATOR, MAX_RETRIES, LLM_TIMEOUT
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.containers.service_container import embedding_service, prompt_service
from app.schemas.analysis_response import RagResult, SearchResult
from app.schemas.document_request import DocumentRequest
from app.services.standard.vector_store import ensure_qdrant_collection

SEARCH_COUNT = 3
VIOLATION_THRESHOLD = 0.6
LLM_REQUIRED_KEYS = {"clause_content", "correctedText", "proofText",
                     "violation_score"}


async def vectorize_and_calculate_similarity_ocr(
    combined_chunks: List[RagResult], document_request: DocumentRequest,
    all_texts_with_bounding_boxes: List[dict]) -> List[RagResult]:
  print(f'combined chunk {combined_chunks}')

  qd_client = get_qdrant_client()
  await ensure_qdrant_collection(qd_client, document_request.categoryName)

  embedding_inputs = []
  for chunk in combined_chunks:
    parts = chunk.incorrect_text.split(ARTICLE_CLAUSE_SEPARATOR, 1)
    title = parts[0].strip() if len(parts) == 2 else ""
    content = parts[1].strip() if len(parts) == 2 else parts[0].strip()
    embedding_inputs.append(f"{title} {content}")

  start_time = time.time()
  embeddings = await embedding_service.batch_embed_texts(
    get_embedding_async_client(), embedding_inputs)
  logging.info(f"임베딩 묶음 소요 시간: {time.time() - start_time}")

  semaphore = asyncio.Semaphore(5)
  prompt_client = get_prompt_async_client()
  tasks = [
    process_clause_ocr(qd_client, prompt_client, chunk, embedding,
                       document_request.categoryName,
                       semaphore, all_texts_with_bounding_boxes)
    for chunk, embedding in zip(combined_chunks, embeddings)
  ]

  # 모든 임베딩 및 유사도 검색 태스크를 병렬로 실행
  results = await asyncio.gather(*tasks)
  return [result for result in results if result is not None]


async def vectorize_and_calculate_similarity(
    combined_chunks: List[RagResult], document_request: DocumentRequest,
    byte_type_pdf: fitz.Document) -> List[RagResult]:

  qd_client = get_qdrant_client()
  await ensure_qdrant_collection(qd_client, document_request.categoryName)

  embedding_inputs = await prepare_embedding_inputs(combined_chunks)

  start_time = time.time()
  async with get_embedding_async_client() as embedding_client:
    embeddings = await embedding_service.batch_embed_texts(
        embedding_client, embedding_inputs)
  logging.info(f"임베딩 묶음 소요 시간: {time.time() - start_time}")

  semaphore = asyncio.Semaphore(5)
  async with get_prompt_async_client() as prompt_client:
    tasks = [
      process_clause(qd_client, prompt_client, chunk, embedding,
                     document_request.categoryName, semaphore, byte_type_pdf)
      for chunk, embedding in zip(combined_chunks, embeddings)
    ]
    results = await asyncio.gather(*tasks)

  success_results: List[RagResult] = [r.result for r in results if
                     r.status == ChunkProcessStatus.SUCCESS and r.result is not None]
  failure_score = sum(r.status == ChunkProcessStatus.FAILURE for r in results)

  if not success_results and failure_score == len(combined_chunks):
    raise AgreementException(ErrorCode.CHUNK_ANALYSIS_FAILED)

  return success_results


async def prepare_embedding_inputs(chunks: List[RagResult]) -> List[str]:
  inputs = []
  for chunk in chunks:
    parts = chunk.incorrect_text.split(ARTICLE_CLAUSE_SEPARATOR, 1)
    title = parts[0].strip() if len(parts) == 2 else ""
    content = parts[1].strip() if len(parts) == 2 else parts[0].strip()
    inputs.append(f"{title} {content}")
  return inputs


async def process_clause(qd_client: AsyncQdrantClient,
    prompt_client: AsyncAzureOpenAI, rag_result: RagResult,
    embedding: List[float], collection_name: str, semaphore: Semaphore,
    byte_type_pdf: fitz.Document) -> ChunkProcessResult:
  search_results = \
    await search_qdrant(semaphore, collection_name, embedding, qd_client)
  clause_results = await gather_search_results(search_results)
  corrected_result = await generate_clause_correction(prompt_client,
                                                      rag_result.incorrect_text,
                                                      clause_results)

  if not corrected_result:
    return ChunkProcessResult(status=ChunkProcessStatus.FAILURE)

  try:
    score = float(corrected_result["violation_score"])
  except (KeyError, ValueError, TypeError):
    logging.warning(f"violation_score 추출 실패")
    return ChunkProcessResult(status=ChunkProcessStatus.FAILURE)

  if score < VIOLATION_THRESHOLD:
    return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS)

  all_positions = \
    await find_text_positions(rag_result, byte_type_pdf)
  # await find_text_positions(rag_result.incorrect_text, byte_type_pdf)
  positions = await extract_positions_by_page(all_positions)

  rag_result.accuracy = score
  rag_result.incorrect_text = await clean_incorrect_text(
      rag_result.incorrect_text)
  rag_result.corrected_text = corrected_result["correctedText"]
  rag_result.proof_text = corrected_result["proofText"]

  rag_result.clause_data[0].position = positions[0]
  if positions[1]:
    rag_result.clause_data[1].position = positions[1]

  return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS,
                            result=rag_result)


async def process_clause_ocr(qd_client: AsyncQdrantClient,
    prompt_client: AsyncAzureOpenAI,
    rag_result: RagResult,
    embedding: List[float], collection_name: str, semaphore: Semaphore,
    all_texts_with_bounding_boxes: List[dict]) -> Optional[RagResult]:
  search_results = \
    await search_qdrant(semaphore, collection_name, embedding, qd_client)
  clause_results = await gather_search_results(search_results)
  corrected_result = \
    await generate_clause_correction(prompt_client, rag_result.incorrect_text, clause_results)

  if not corrected_result:
    return None

  try:
    score = float(corrected_result["violation_score"])
  except (KeyError, ValueError, TypeError):
    logging.warning(f"violation_score 추출 실패")
    return None

  if score < VIOLATION_THRESHOLD:
    return None

  all_positions = \
    await find_text_positions_ocr(rag_result.incorrect_text,
                                  all_texts_with_bounding_boxes)

  rag_result.accuracy = score
  rag_result.incorrect_text = await clean_incorrect_text(
      rag_result.incorrect_text)
  rag_result.corrected_text = corrected_result["correctedText"]
  rag_result.proof_text = corrected_result["proofText"]

  print(f'Length of clause_data: {len(rag_result.clause_data)}')
  print(f'all_positions : {all_positions}')
  print(f'type all_positions : {type(all_positions)}')

  rag_result.clause_data[0].position.extend(all_positions)

  print(f"Updated rag_result: {rag_result}")
  return rag_result


async def search_qdrant(semaphore: Semaphore, collection_name: str,
    embedding: List[float],
    qd_client: AsyncQdrantClient) -> QueryResponse:
  for attempt in range(1, MAX_RETRIES + 1):
    try:
      async with semaphore:
        search_results = await qd_client.query_points(
            collection_name=collection_name,
            query=embedding,
            search_params=models.SearchParams(hnsw_ef=128, exact=False),
            limit=SEARCH_COUNT,
            with_payload=["incorrect_text", "corrected_text", "proof_text"]
        )
      break
    except Exception as e:
      if attempt == MAX_RETRIES:
        raise CommonException(ErrorCode.QDRANT_SEARCH_FAILED)
      logging.warning(
          f"query_points: Qdrant Search 재요청 발생 {attempt}/{MAX_RETRIES} {e}")
      await asyncio.sleep(1)

  if search_results is None:
    raise AgreementException(ErrorCode.NO_POINTS_FOUND)

  return search_results


async def gather_search_results(search_results: QueryResponse) -> List[
  SearchResult]:
  clause_results = []
  for match in search_results.points:
    payload_data = match.payload or {}

    if not isinstance(payload_data, dict):
      logging.warning(f"search_results dict 타입 반환 안됨: {type(payload_data)}")
      continue

    clause_results.append(
        SearchResult(
            proof_text=payload_data.get("proof_text", ""),
            incorrect_text=payload_data.get("incorrect_text", ""),
            corrected_text=payload_data.get("corrected_text", "")
        ))

  return clause_results


async def generate_clause_correction(prompt_client: AsyncAzureOpenAI,
    article_content: str, clause_results: List[SearchResult]) -> Optional[
  dict[str, Any]]:
  for attempt in range(1, MAX_RETRIES + 1):
    try:
      result = await asyncio.wait_for(
          prompt_service.correct_contract(
              prompt_client,
              clause_content=article_content,
              proof_text=[item.proof_text for item in clause_results],  # 기준 문서들
              incorrect_text=[item.incorrect_text for item in clause_results],
              corrected_text=[item.corrected_text for item in clause_results]
          ),
          timeout=LLM_TIMEOUT
      )
      if isinstance(result, dict) and LLM_REQUIRED_KEYS.issubset(result.keys()):
        return result
      logging.warning(f"[generate_clause_correction]: llm 응답 필수 키 누락됨")

    except Exception as e:
      if isinstance(e, asyncio.TimeoutError):
        if attempt == MAX_RETRIES:
          raise CommonException(ErrorCode.LLM_RESPONSE_TIMEOUT)
      else:
        if attempt == MAX_RETRIES:
          raise AgreementException(ErrorCode.AGREEMENT_REVIEW_FAIL)
        logging.warning(
            f"query_points: 계약서 LLM 재요청 발생 {attempt}/{MAX_RETRIES} {e}")
        await asyncio.sleep(0.5 * attempt)

  return None


async def clean_incorrect_text(text: str) -> str:
  return (
    text.split(ARTICLE_CLAUSE_SEPARATOR, 1)[-1]
    .replace(CLAUSE_TEXT_SEPARATOR, "")
    .replace("\n", "")
    .replace("", '"')
  )


async def find_text_positions(rag_result: RagResult,
    pdf_document: fitz.Document) -> dict[int, List[dict]]:
  all_positions = {}  # 페이지별로 위치 정보를 저장할 딕셔너리

  # +를 기준으로 문장을 나누고 뒤에 있는 부분만 사용
  clause_content_parts = rag_result.incorrect_text.split('+', 1)
  if len(clause_content_parts) > 1:
    rag_result.incorrect_text = clause_content_parts[1].strip()  # `+` 뒤의 내용만 사용

  # "!!!"을 기준으로 더 나눠서 각각을 위치 찾기
  clause_parts = rag_result.incorrect_text.split('!!!')

  # 모든 페이지를 검색
  for clause_part in rag_result.clause_data:
    page = pdf_document.load_page(clause_part.page - 1)  # 페이지 로드

    # 페이지 크기 얻기 (페이지의 너비와 높이)
    page_width = float(page.rect.width)  # 명시적으로 float로 처리
    page_height = float(page.rect.height)  # 명시적으로 float로 처리

    page_positions = []  # 현재 페이지에 대한 위치 정보를 담을 리스트

    # 각 문장에 대해 위치를 찾기
    for part in clause_parts:
      part = part.strip()  # 앞뒤 공백 제거
      if part == "":
        continue

      # 문장의 위치를 찾기 위해 search_for 사용
      text_instances = page.search_for(part)

      # y값을 기준으로 묶을 변수
      grouped_positions = {}

      # 텍스트 인스턴스들에 대해 위치 정보를 추출
      for text_instance in text_instances:
        x0, y0, x1, y1 = text_instance  # 바운딩 박스 좌표

        # 상대적인 위치로 계산 (픽셀을 페이지 크기로 나누어 상대값 계산)
        rel_x0 = x0 / page_width
        rel_y0 = y0 / page_height
        rel_x1 = x1 / page_width
        rel_y1 = y1 / page_height

        # y 값을 기준으로 그룹화
        if rel_y0 not in grouped_positions:
          grouped_positions[rel_y0] = []

        grouped_positions[rel_y0].append((rel_x0, rel_x1, rel_y0, rel_y1))

      # 그룹화된 바운딩 박스를 하나의 큰 박스로 묶기
      for y_key, group in grouped_positions.items():
        # 하나의 그룹에서 x0, x1의 최솟값과 최댓값을 구하기
        min_x0 = min([x[0] for x in group])  # 최소 x0 값
        max_x1 = max([x[1] for x in group])  # 최대 x1 값

        # 하나의 그룹에서 y0, y1의 최솟값과 최댓값을 구하기
        min_y0 = min([x[2] for x in group])  # 최소 y0 값
        max_y1 = max([x[3] for x in group])  # 최대 y1 값

        # 상대적인 값에 100을 곱해줍니다
        min_x0 *= 100
        min_y0 *= 100
        max_x1 *= 100
        max_y1 *= 100

        width = max_x1 - min_x0
        height = max_y1 - min_y0

        # 바운딩 박스를 생성 (최소값과 최대값을 사용)
        page_positions.append({
          "page": clause_part.page,
          "bbox": (min_x0, min_y0, width, height)  # 상대적 x, y, 너비, 높이
        })

    # 페이지별로 위치를 딕셔너리에 추가
    if page_positions:
      all_positions[clause_part.page] = page_positions

  return all_positions


async def find_text_positions_ocr(clause_content: str,
    all_texts_with_bounding_boxes: List[dict]) -> List[dict]:
  epsilon = None
  all_positions = {}  # 페이지별로 위치 정보를 저장할 딕셔너리

  # +를 기준으로 문장을 나누고 뒤에 있는 부분만 사용
  clause_content_parts = clause_content.split('+', 1)
  if len(clause_content_parts) > 1:
    clause_content = clause_content_parts[1].strip()  # `+` 뒤의 내용만 사용
  print(f'clause_content : {clause_content}')

  full_text = " ".join([item['text'] for item in all_texts_with_bounding_boxes])

  if clause_content in full_text:  # 해당 문장이 전체 텍스트에 포함되어 있는지 확인

    # 검색 범위의 시작과 끝 인덱스를 찾음
    search_start_idx = full_text.find(clause_content)
    search_end_idx = search_start_idx + len(clause_content)
    print(
        f'Search text "{clause_content}" is located from index {search_start_idx} to {search_end_idx} in full text.')

    search_text_parts = clause_content.split()  # 텍스트 조각을 분리 (공백 기준)

    # y값 기준으로 텍스트를 그룹화
    grouped_texts = {}

    # 검색 시작 인덱스
    start_idx = search_start_idx  # 처음에는 전체 검색 범위의 시작 인덱스로 시작
    last_end_idx = -1  # 이전 끝 인덱스를 저장할 변수 초기화

    # 전체 바운딩 박스 변수 초기화
    max_x_total = float('-inf')
    max_y_total = float('-inf')
    min_x_total = float('inf')
    min_y_total = float('inf')

    # 검색 시작
    for item in all_texts_with_bounding_boxes:
      print(f'item : {item}')

      for part in search_text_parts:
        if part == item['text']:  # 부분 텍스트 일치
          print(f'item["text"] {item["text"]}')

          # 첫 번째 단어는 처음부터 검색
          if last_end_idx == -1:  # 처음에는 0부터 검색
            start_idx = 0
          else:
            # 중복되는 단어는 이전 검색에서 찾은 끝 인덱스 이후부터 시작
            start_idx = last_end_idx

          item_text_start_idx = full_text.find(part,
                                               start_idx)  # 각 단어의 시작 인덱스를 찾음
          if item_text_start_idx == -1:
            break  # 더 이상 찾을 것이 없으면 종료
          item_text_end_idx = item_text_start_idx + len(part)

          print(
              f'start_idx {start_idx} item_text_start_idx {item_text_start_idx}')
          print(f'start_idx : {start_idx}')
          print(f'search_end_idx : {search_end_idx}')
          print(f'item_text_start_idx : {item_text_start_idx}')
          print(f'item_text_end_idx : {item_text_end_idx}')

          # 텍스트가 정확히 검색 범위 내에 있을 경우만 처리
          if search_start_idx <= item_text_start_idx and search_end_idx >= item_text_end_idx:
            print(f'Found "{part}" in the search text range.')

            bounding_box = item['bounding_box']
            print(f'bounding_box: {bounding_box}')

            for vertex in bounding_box:
              center_y = (sum(vertex['y'] for vertex in bounding_box)
                          / len(bounding_box))

              # 첫 단어일 때만 높이 비율 기반 동적 epsilon 설정
              if epsilon is None:
                y_values = [vertex['y'] for vertex in bounding_box]
                height_ratio = max(y_values) - min(y_values)
                epsilon = height_ratio / 2
                print(f"[✔] dynamic_epsilon 설정됨 (비율): {epsilon:.4f}")

              # y값 기준으로 그룹화 (epsilon 값으로 오차 범위 설정)
              group_found = False
              for y_group in grouped_texts:
                if center_y > y_group - (
                    epsilon) and center_y < y_group + (
                    epsilon):
                  grouped_texts[y_group].append(item)
                  group_found = True
                  break

              if not group_found:
                grouped_texts[center_y] = [item]

            # 한 번 단어를 찾고 나면, 다음 검색을 위해 item_text_start_idx를 이동시킴
            item_text_start_idx += len(part)

            last_end_idx = item_text_end_idx
            start_idx = last_end_idx  # 시작 인덱스를 갱신
            print(f"Updated start_idx: {start_idx}")

            # 찾은 단어가 범위 내에 있을 때 바로 루프 종료
            break

          # 다음 인덱스부터 검색을 계속 진행
          last_end_idx = item_text_end_idx  # 이전 시작 인덱스부터 새로운 시작 위치로 갱신
          start_idx = last_end_idx  # 시작 인덱스를 갱신
          print(f"Updated start_idx: {start_idx}")
          break

    points_list = []
    unique_relative_points = set()
    # 그룹화된 텍스트에 대해 바운딩 박스를 계산
    for y_group in grouped_texts:
      min_x_group = float('inf')
      min_y_group = float('inf')
      max_x_group = float('-inf')
      max_y_group = float('-inf')

      # 그룹에 속한 텍스트들의 바운딩 박스를 계산
      for item in grouped_texts[y_group]:
        bounding_box = item['bounding_box']
        for vertex in bounding_box:
          abs_x = vertex['x']
          abs_y = vertex['y']

          min_x_group = min(min_x_group, abs_x)
          min_y_group = min(min_y_group, abs_y)
          max_x_group = max(max_x_group, abs_x)
          max_y_group = max(max_y_group, abs_y)

      # 바운딩 박스 계산
      min_x = min_x_group * 100
      min_y = min_y_group * 100
      width = (max_x_group - min_x_group) * 100
      height = (max_y_group - min_y_group) * 100

      points = np.array([[min_x, min_y, width, height]], np.float64)

      points_tuple = tuple(points[0])

      if points_tuple not in unique_relative_points:
        unique_relative_points.add(points_tuple)
        points_list.append(points[0].tolist())

  return points_list


async def extract_positions_by_page(all_positions: dict[int, List[dict]]) -> \
    List[List]:
  positions = [[], []]
  first_page = None

  # `rag_result.clause_data`에 두 개만 저장
  for page_num, positions_in_page in all_positions.items():
    # 첫 번째 문장이 시작되는 페이지를 찾으면 첫 번째 위치에 저장
    if first_page is None:
      first_page = page_num
      positions[0].extend(p['bbox'] for p in positions_in_page)
    else:
      # 첫 번째 문장이 시작된 후, 페이지가 변경되면 두 번째 위치에 저장
      if page_num != first_page:
        positions[1].extend(p['bbox'] for p in positions_in_page)

  return positions


async def extract_positions_ocr(all_positions: dict[int, List[dict]]) -> \
    List[List]:
  positions = [[], []]
  first_page = None

  # `rag_result.clause_data`에 두 개만 저장
  for page_num, positions_in_page in all_positions.items():
    # 첫 번째 문장이 시작되는 페이지를 찾으면 첫 번째 위치에 저장
    if first_page is None:
      first_page = page_num
      positions[0].extend(p['bbox'] for p in positions_in_page)
    else:
      # 첫 번째 문장이 시작된 후, 페이지가 변경되면 두 번째 위치에 저장
      if page_num != first_page:
        positions[1].extend(p['bbox'] for p in positions_in_page)

  return positions
