import asyncio
import logging
from asyncio import Semaphore
from typing import List, Optional, Any
import fitz

from qdrant_client import models, AsyncQdrantClient
from qdrant_client.http.models import QueryResponse

from app.blueprints.agreement.agreement_exception import AgreementException
from app.clients.openai_clients import get_prompt_async_client, \
  get_embedding_async_client
from app.clients.qdrant_client import get_qdrant_client
from app.common.chunk_status import ChunkProcessResult, ChunkProcessStatus
from app.common.constants import ARTICLE_CLAUSE_SEPARATOR, \
  CLAUSE_TEXT_SEPARATOR, MAX_RETRIES
from app.common.decorators import async_measure_time
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.containers.service_container import embedding_service, prompt_service
from app.schemas.analysis_response import RagResult, SearchResult
from app.schemas.document_request import DocumentRequest
from app.services.common.llm_retry import retry_llm_call
from app.services.common.qdrant_utils import ensure_qdrant_collection

SEARCH_COUNT = 3
VIOLATION_THRESHOLD = 0.75
LLM_REQUIRED_KEYS = {"clause_content", "correctedText", "proofText",
                     "violation_score"}


async def vectorize_and_calculate_similarity_ocr(
    combined_chunks: List[RagResult], document_request: DocumentRequest,
    all_texts_with_bounding_boxes: List[dict]) -> List[RagResult]:

  qd_client = get_qdrant_client()
  await ensure_qdrant_collection(qd_client, document_request.categoryName)

  embedding_inputs = []
  for chunk in combined_chunks:
    parts = chunk.incorrect_text.split(ARTICLE_CLAUSE_SEPARATOR, 1)
    title = parts[0].strip() if len(parts) == 2 else ""
    content = parts[1].strip() if len(parts) == 2 else parts[0].strip()
    embedding_inputs.append(f"{title} {content}")

  async with get_embedding_async_client() as embedding_client:
    embeddings = await embedding_service.batch_embed_texts(
      embedding_client, embedding_inputs)

  semaphore = asyncio.Semaphore(5)
  tasks = [
    process_clause_ocr(qd_client, chunk, embedding,
                       document_request.categoryName,
                       semaphore, all_texts_with_bounding_boxes)
    for chunk, embedding in zip(combined_chunks, embeddings)
  ]

  # 모든 임베딩 및 유사도 검색 태스크를 병렬로 실행
  results = await asyncio.gather(*tasks)

  success_results: List[RagResult] = [r.result for r in results if
                     r.status == ChunkProcessStatus.SUCCESS and r.result is not None]
  failure_score = sum(r.status == ChunkProcessStatus.FAILURE for r in results)

  if not success_results and failure_score == len(combined_chunks):
    raise AgreementException(ErrorCode.CHUNK_ANALYSIS_FAILED)

  return success_results


@async_measure_time
async def vectorize_and_calculate_similarity(
    combined_chunks: List[RagResult], document_request: DocumentRequest,
    byte_type_pdf: fitz.Document) -> List[RagResult]:

  qd_client = get_qdrant_client()
  await ensure_qdrant_collection(qd_client, document_request.categoryName)

  embedding_inputs = await prepare_embedding_inputs(combined_chunks)

  async with get_embedding_async_client() as embedding_client:
    embeddings = await embedding_service.batch_embed_texts(
        embedding_client, embedding_inputs)

  tasks = [
    process_clause(qd_client, chunk, embedding,
                   document_request.categoryName, byte_type_pdf)
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


async def process_clause(qd_client: AsyncQdrantClient, rag_result: RagResult,
    embedding: List[float], collection_name: str,
    byte_type_pdf: fitz.Document) -> ChunkProcessResult:
  semaphore = asyncio.Semaphore(5)
  search_results = await search_qdrant(semaphore, collection_name, embedding,
                                       qd_client)
  parse_incorrect_text(rag_result)

  async with get_prompt_async_client() as prompt_client:
    corrected_result = await retry_llm_call(
        prompt_service.correct_contract,
        prompt_client, rag_result.incorrect_text.replace("\n", " "),
        search_results,
        required_keys=LLM_REQUIRED_KEYS
    )
  if not corrected_result:
    return ChunkProcessResult(status=ChunkProcessStatus.FAILURE)

  try:
    score = float(corrected_result["violation_score"])
  except (KeyError, ValueError, TypeError):
    logging.warning(f"violation_score 추출 실패")
    return ChunkProcessResult(status=ChunkProcessStatus.FAILURE)

  if score < VIOLATION_THRESHOLD:
    return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS)

  rag_result.accuracy = score
  rag_result.incorrect_part = corrected_result["incorrectPart"]
  all_positions, part_position = \
    await find_text_positions(rag_result,byte_type_pdf)
  positions = await extract_positions_by_page(all_positions)
  part_positions = await extract_positions_by_page(part_position)

  set_result_data(corrected_result, rag_result, positions, part_positions)
  if any(not clause.position for clause in rag_result.clause_data):
    logging.warning(f"원문 일치 position값 불러오지 못함")
    return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS)

  return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS,
                            result=rag_result)

async def extract_incorrect_text(rag_result: RagResult) -> str:
  clause_content_parts = rag_result.incorrect_text.split(ARTICLE_CLAUSE_SEPARATOR, 1)
  return clause_content_parts[1].strip() if len(clause_content_parts) > 1 else ""


async def process_clause_ocr(qd_client: AsyncQdrantClient,
    rag_result: RagResult, embedding: List[float], collection_name: str, semaphore: Semaphore,
    all_texts_with_bounding_boxes: List[dict]) -> ChunkProcessResult:

  semaphore = asyncio.Semaphore(5)
  search_results = \
    await search_qdrant(semaphore, collection_name, embedding, qd_client)

  parse_incorrect_text(rag_result)

  async with get_prompt_async_client() as prompt_client:
    corrected_result = await retry_llm_call(
        prompt_service.correct_contract,
        prompt_client, rag_result.incorrect_text.replace("\n", " "),
        search_results,
        required_keys=LLM_REQUIRED_KEYS
    )
  if not corrected_result:
    return ChunkProcessResult(status=ChunkProcessStatus.FAILURE)

  try:
    score = float(corrected_result["violation_score"])
  except (KeyError, ValueError, TypeError):
    logging.warning(f"violation_score 추출 실패")
    return ChunkProcessResult(status=ChunkProcessStatus.FAILURE)

  if score < VIOLATION_THRESHOLD:
    return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS)

  rag_result.incorrect_part = corrected_result["incorrectPart"]

  all_positions, part_position = \
    await find_text_positions_ocr(rag_result,
                                  all_texts_with_bounding_boxes)

  rag_result.accuracy = score
  rag_result.corrected_text = corrected_result["correctedText"]
  rag_result.proof_text = corrected_result["proofText"]

  rag_result.clause_data[0].position.extend(all_positions)
  rag_result.clause_data[0].position_part.extend(part_position)

  # 왜 해당 코드 에러
  return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS,
                            result=rag_result)


def parse_incorrect_text(rag_result: RagResult) -> None:
  try:
    clause_parts = rag_result.incorrect_text.split(
        ARTICLE_CLAUSE_SEPARATOR, 1)
  except Exception:
    raise AgreementException(ErrorCode.NO_SEPARATOR_FOUND)

  rag_result.incorrect_text = clause_parts[-1]
  rag_result.incorrect_text = rag_result.incorrect_text.replace("\n", "") # 여기서


async def search_qdrant(semaphore: Semaphore, collection_name: str,
    embedding: List[float],
    qd_client: AsyncQdrantClient) -> List[SearchResult]:
  search_results = await search_collection(qd_client, semaphore,
                                           collection_name, embedding)
  legal_term_results = await search_collection(qd_client, semaphore,
                                               "법률용어", embedding)
  return gather_search_results(search_results, legal_term_results)


async def search_collection(qd_client: AsyncQdrantClient,
    semaphore: Semaphore, collection_name: str,
    embedding: List[float]) -> QueryResponse:
  for attempt in range(1, MAX_RETRIES + 1):
    try:
      async with semaphore:
        search_results = await qd_client.query_points(
            collection_name=collection_name,
            query=embedding,
            search_params=models.SearchParams(hnsw_ef=128, exact=False),
            limit=SEARCH_COUNT,
            with_payload=True
        )
      break
    except Exception as e:
      if attempt == MAX_RETRIES:
        raise CommonException(ErrorCode.QDRANT_SEARCH_FAILED)
      logging.warning(
          f"[search_collection]: Qdrant Search 재요청 발생 {attempt}/{MAX_RETRIES} {e}")
      await asyncio.sleep(1)

  if search_results is None or not search_results.points:
    raise AgreementException(ErrorCode.NO_POINTS_FOUND)

  return search_results


def gather_search_results(search_results: QueryResponse,
    legal_term_results: QueryResponse) -> List[
  SearchResult]:
  merged_results: List[SearchResult] = []

  for i in range(SEARCH_COUNT):
    clause_payload = search_results.points[i].payload if i < len(
        search_results.points) else {}
    term_payload = legal_term_results.points[i].payload if i < len(
        legal_term_results.points) else {}

    merged_results.append(
        SearchResult(
            proof_text=clause_payload.get("proof_text", ""),
            incorrect_text=clause_payload.get("incorrect_text", ""),
            corrected_text=clause_payload.get("corrected_text", ""),
            term=term_payload.get("term", ""),
            meaning_difference=term_payload.get("meaning_difference", ""),
            definition=term_payload.get("definition", ""),
            keywords=term_payload.get("keywords", "")
        )
    )

  return merged_results


def is_correct_response_format(result: dict[str, str]) -> bool:
  return (
      isinstance(result, dict)
      and LLM_REQUIRED_KEYS.issubset(result.keys())
      and all(isinstance(result[key], str) for key in LLM_REQUIRED_KEYS)
  )


def set_result_data(corrected_result: Optional[
  dict[str, Any]], rag_result: RagResult, positions: List[List],
    part_positions: List[List]):

  rag_result.incorrect_text = (
    rag_result.incorrect_text.split(ARTICLE_CLAUSE_SEPARATOR, 1)[-1]
    .replace(CLAUSE_TEXT_SEPARATOR, "")
    .replace("\n", "")
    .replace("", '"')
  )

  value = corrected_result["incorrectPart"]
  rag_result.incorrect_part = " ".join(value) if isinstance(value,
                                                            list) else value
  value = corrected_result["correctedText"]
  rag_result.corrected_text = " ".join(value) if isinstance(value,
                                                            list) else value
  value = corrected_result["proofText"]
  rag_result.proof_text = " ".join(value) if isinstance(value, list) else value

  rag_result.clause_data[0].position = positions[0]
  if positions[1]:
    rag_result.clause_data[1].position = positions[1]

  rag_result.clause_data[0].position_part = part_positions[0]
  if positions[1]:
    rag_result.clause_data[1].position_part = part_positions[1]


def search_text_in_pdf(text: str, pdf_doc: fitz.Document, clause_data,
    is_relative=True) -> dict[int, List[dict]]:
  positions_by_page = {}
  # 페이지별 검색
  for clause_part in clause_data:
    page_num = clause_part.page
    page = pdf_doc.load_page(page_num - 1)

    page_width = float(page.rect.width)
    page_height = float(page.rect.height)

    page_positions = []

    # 바로 검색
    text_instances = page.search_for(text.strip())
    grouped_positions = {}

    for inst in text_instances:
      x0, y0, x1, y1 = inst

      # 상대값 또는 절대값으로 처리
      if is_relative:
        rel_x0 = x0 / page_width
        rel_y0 = y0 / page_height
        rel_x1 = x1 / page_width
        rel_y1 = y1 / page_height
      else:
        rel_x0, rel_y0, rel_x1, rel_y1 = x0, y0, x1, y1

      if rel_y0 not in grouped_positions:
        grouped_positions[rel_y0] = []

      grouped_positions[rel_y0].append((rel_x0, rel_x1, rel_y0, rel_y1))

    for y_key, group in grouped_positions.items():
      min_x0 = min(x[0] for x in group)
      max_x1 = max(x[1] for x in group)
      min_y0 = min(x[2] for x in group)
      max_y1 = max(x[3] for x in group)

      # 상대값이면 100배
      if is_relative:
        min_x0 *= 100
        min_y0 *= 100
        max_x1 *= 100
        max_y1 *= 100

      width = max_x1 - min_x0
      height = max_y1 - min_y0

      # 바운딩 박스를 생성 (최소값과 최대값을 사용)
      page_positions.append({
        "page": page_num,
        "bbox": (min_x0, min_y0, width, height)
      })

    if page_positions:
      positions_by_page[page_num] = page_positions

  return positions_by_page


async def find_text_positions(rag_result: RagResult,
    pdf_document: fitz.Document) -> dict[str, dict[int, List[dict]]]:

  # incorrect_text 처리 (all_positions 용)
  clause_content_parts = rag_result.incorrect_text.split('+', 1)
  if len(clause_content_parts) > 1:
    rag_result.incorrect_text = clause_content_parts[1].strip()

  clause_parts = rag_result.incorrect_text.split('!!!')

  # 전체 문장 기준으로 검색
  all_positions = {}
  part_positions = {}
  for part in clause_parts:
    part = part.strip()
    if part == "":
      continue
    partial_result = search_text_in_pdf(part, pdf_document,
                                        rag_result.clause_data)
    for page, boxes in partial_result.items():
      if page not in all_positions:
        all_positions[page] = []
      all_positions[page].extend(boxes)

  # incorrect_part는 그대로 검색
  part_position = search_text_in_pdf(rag_result.incorrect_part, pdf_document,
                                      rag_result.clause_data)
  for page, boxes in part_position.items():
    if page not in part_positions:
      part_positions[page] = []
    part_positions[page].extend(boxes)

  return all_positions, part_positions



async def find_text_positions_ocr(rag_result: RagResult,
    all_texts_with_bounding_boxes: List[dict]) -> tuple[List[tuple], List[tuple]]:


  # +를 기준으로 문장을 나누고 뒤에 있는 부분만 사용
  clause_content = rag_result.incorrect_text.split('+', 1)
  if len(clause_content) > 1:
    rag_result.incorrect_text = clause_content[1].strip()

  # +를 기준으로 문장을 나누고 뒤에 있는 부분만 사용
  part_clause_content = rag_result.incorrect_part.split('+', 1)
  if len(part_clause_content) > 1:
    rag_result.incorrect_part = part_clause_content[1].strip()

  all_positions, part_positions = extract_bbox_positions(rag_result.incorrect_text,
                                                         rag_result.incorrect_part,
                                                         all_texts_with_bounding_boxes)

  return all_positions, part_positions


def extract_bbox_positions(
    clause_content: str,
    incorrect_part: str,
    all_texts_with_bounding_boxes: List[dict]
) -> tuple[List[tuple], List[tuple]]:
  full_text = " ".join(item['text'] for item in all_texts_with_bounding_boxes)

  def get_position_range(target_text: str, base_start: int = 0) -> tuple[
    int, int]:
    start_idx = full_text.find(target_text, base_start)
    end_idx = start_idx + len(target_text) if start_idx != -1 else -1
    return start_idx, end_idx

  def extract_bboxes(start_idx: int, end_idx: int) -> List[tuple]:
    epsilon = None

    matched_items = [
      item for item in all_texts_with_bounding_boxes
      if start_idx <= item['start_idx'] < end_idx
    ]

    grouped_texts = {}
    for item in matched_items:
      bounding_box = item['bounding_box']
      center_y = sum(vertex['y'] for vertex in bounding_box) / len(bounding_box)

      if epsilon is None:
        y_values = [vertex['y'] for vertex in bounding_box]
        group_height = max(y_values) - min(y_values)
        epsilon = group_height * 0.5

      abs_center_y = center_y
      group_found = False
      for y_group in grouped_texts:
        if y_group - epsilon < abs_center_y < y_group + epsilon:
          grouped_texts[y_group].append(item)
          group_found = True
          break
      if not group_found:
        grouped_texts[abs_center_y] = [item]

    points_list = []
    unique_relative_points = set()
    for y_group in grouped_texts:
      min_x_group = float('inf')
      min_y_group = float('inf')
      max_x_group = float('-inf')
      max_y_group = float('-inf')

      for item in grouped_texts[y_group]:
        for vertex in item['bounding_box']:
          abs_x = vertex['x']
          abs_y = vertex['y']
          min_x_group = min(min_x_group, abs_x)
          min_y_group = min(min_y_group, abs_y)
          max_x_group = max(max_x_group, abs_x)
          max_y_group = max(max_y_group, abs_y)

      min_x = min_x_group * 100
      min_y = min_y_group * 100
      width = (max_x_group - min_x_group) * 100
      height = (max_y_group - min_y_group) * 100

      points_tuple = (min_x, min_y, width, height)
      if points_tuple not in unique_relative_points:
        unique_relative_points.add(points_tuple)
        points_list.append(points_tuple)

    return points_list

  # 전체 문장 기준
  clause_start_idx, clause_end_idx = get_position_range(clause_content)
  # 부분 문장은 전체 문장 안에서만 찾기
  part_start_idx, part_end_idx = get_position_range(incorrect_part,
                                                    clause_start_idx)

  all_positions = extract_bboxes(clause_start_idx, clause_end_idx)
  part_positions = extract_bboxes(part_start_idx, part_end_idx)

  return all_positions, part_positions


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

