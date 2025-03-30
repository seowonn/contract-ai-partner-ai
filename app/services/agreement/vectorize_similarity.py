import asyncio
import logging
from asyncio import Semaphore
from typing import List, Optional

from qdrant_client import models

from app.clients.qdrant_client import get_qdrant_client
from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.schemas.analysis_response import RagResult
from app.schemas.document_request import DocumentRequest
from app.containers.service_container import embedding_service, prompt_service
from app.services.standard.vector_store import ensure_qdrant_collection
import fitz


async def vectorize_and_calculate_similarity(
    sorted_chunks: List[RagResult],
    collection_name: str, document_request: DocumentRequest,
    pdf_document: fitz.Document) -> List[RagResult]:
  await ensure_qdrant_collection(collection_name)

  semaphore = asyncio.Semaphore(3)  # 딱 한 번만 생성
  tasks = []
  for chunk in sorted_chunks:
    tasks.append(process_clause(chunk, chunk.incorrect_text, collection_name,
                                document_request.categoryName, semaphore,
                                pdf_document))

  # 모든 임베딩 및 유사도 검색 태스크를 병렬로 실행
  results = await asyncio.gather(*tasks)
  return [result for result in results if result is not None]


async def process_clause(rag_result: RagResult, clause_content: str,
    collection_name: str, category_name: str, semaphore: Semaphore,
    pdf_document: fitz.Document) -> Optional[RagResult]:
  embedding = await embedding_service.embed_text(clause_content)

  client = get_qdrant_client()
  for retry in range(2):
    try:
      async with semaphore:
        search_results = await client.query_points(
            collection_name=collection_name,
            query=embedding,
            query_filter=models.Filter(
                must=[models.FieldCondition(
                    key="category",
                    match=models.MatchValue(value=category_name)
                )]
            ),
            search_params=models.SearchParams(hnsw_ef=128, exact=False),
            limit=5
        )
      break
    except Exception as e:
      if retry == 1:
        raise BaseCustomException(ErrorCode.QDRANT_SEARCH_FAILED)
      logging.warning(f"query_points: Qdrant Search 재요청 발생 {e}")
      await asyncio.sleep(1)


  # 3️⃣ 유사한 문장들 처리
  clause_results = []
  for match in search_results.points:
    try:
      payload_data = match.payload or {}
      clause_results.append({
        "id": match.id,  # ✅ 벡터 ID
        "proof_text": payload_data.get("proof_text", ""),  # ✅ 원본 문장
        "incorrect_text": payload_data.get("incorrect_text", ""),  # ✅ 잘못된 문장
        "corrected_text": payload_data.get("corrected_text", "")  # ✅ 교정된 문장
      })
    except Exception as e:
      logging.error(f"[process_clause]: {e}")
      continue

  # 4️⃣ 계약서 문장을 수정 (해당 조항의 TOP 5개 유사 문장을 기반으로)
  corrected_result = await prompt_service.correct_contract(
      clause_content=clause_content,
      proof_text=[item["proof_text"] for item in clause_results],  # 기준 문서들
      incorrect_text=[item["incorrect_text"] for item in clause_results],
      corrected_text=[item["corrected_text"] for item in clause_results]
  )

  if not corrected_result:
    return None

  # accuracy가 0.5 이하일 경우 결과를 반환하지 않음
  if float(corrected_result["accuracy"]) > 0.5:

    # 원문 텍스트에 대한 위치 정보 찾기
    all_positions = await find_text_positions(clause_content, pdf_document)

    # 페이지를 기준으로 position을 나누어 저장할 리스트
    positions = [[], []] 

    first_page = None  # 첫 번째 문장이 시작되는 페이지를 추적

    # `rag_result.clause_data`에 두 개만 저장
    for page_num, positions_in_page in all_positions.items():
      # 첫 번째 문장이 시작되는 페이지를 찾으면 첫 번째 위치에 저장
      if first_page is None:
        first_page = page_num
        for position in positions_in_page:
          positions[0].append(position['bbox'])  # 첫 번째 페이지에 저장
      else:
        # 첫 번째 문장이 시작된 후, 페이지가 변경되면 두 번째 위치에 저장
        if page_num != first_page:
          for position in positions_in_page:
            positions[1].append(position['bbox'])  # 두 번째 페이지에 저장

    # `rag_result.clause_data`에 위치 정보 저장
    rag_result.accuracy = float(corrected_result["accuracy"])
    rag_result.corrected_text = corrected_result["corrected_text"]
    rag_result.proof_text = corrected_result["proof_text"]


    rag_result.clause_data[0].position = positions[0]

    # 문장이 다음페이지로 넘어가는 경우에만 [1] 에 저장
    if positions[1]:
        rag_result.clause_data[1].position = positions[1]

    return rag_result

  else:
    # accuracy가 0.5 이하일 경우 빈 객체 반환
    return None




async def find_text_positions(clause_content: str,
    pdf_document: fitz.Document):
  all_positions = {}  # 페이지별로 위치 정보를 저장할 딕셔너리

  # +를 기준으로 문장을 나누고 뒤에 있는 부분만 사용
  clause_content_parts = clause_content.split('+', 1)
  if len(clause_content_parts) > 1:
    clause_content = clause_content_parts[1].strip()  # `+` 뒤의 내용만 사용

  # "!!!"을 기준으로 더 나눠서 각각을 위치 찾기
  clause_parts = clause_content.split('!!!')

  # 모든 페이지를 검색
  for page_num in range(pdf_document.page_count):
    page = pdf_document.load_page(page_num)  # 페이지 로드

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
          "page": page_num + 1,
          "bbox": (min_x0, min_y0, width, height)  # 상대적 x, y, 너비, 높이
        })

    # 페이지별로 위치를 딕셔너리에 추가
    if page_positions:
      all_positions[page_num + 1] = page_positions

  return all_positions