import asyncio
from typing import List

from qdrant_client import models

from app.clients.qdrant_client import qdrant_db_client
from app.schemas.analysis_response import RagResult
from app.schemas.chunk_schema import DocumentChunk
from app.schemas.document_request import DocumentRequest
from app.containers.service_container import embedding_service, prompt_service
from app.services.standard.vector_store import ensure_qdrant_collection
import fitz
import io

# 이걸 pdf_bytes_io 객체를 가져와서 여기서 오픈하는게 맞는건지 모르겠음
pdf_document = fitz.open('./pdf/test.pdf')


async def vectorize_and_calculate_similarity(
    document_chunks: List[DocumentChunk],
    collection_name: str, document_request: DocumentRequest,
    ) -> List[RagResult]:
  await ensure_qdrant_collection(collection_name)

  tasks = []
  for chunk in document_chunks:
    if len(chunk.clause_content) <= 1:
      continue

    rag_result = RagResult(
        page=chunk.page,
        order_index=chunk.order_index
    )
    tasks.append(process_clause(rag_result, chunk.clause_content,
                                collection_name, document_request.categoryName))

  # 모든 임베딩 및 유사도 검색 태스크를 병렬로 실행
  results = await asyncio.gather(*tasks)
  return [result for result in results if result is not None]


async def process_clause(rag_result: RagResult, clause_content: str,
    collection_name: str, category_name: str):
  embedding = await embedding_service.embed_text(clause_content)

  search_results = await qdrant_db_client.query_points(
      collection_name=collection_name,
      query=embedding,
      query_filter=models.Filter(
          must=[
            models.FieldCondition(
                key="category",
                match=models.MatchValue(value=category_name)
            )
          ]
      ),
      search_params=models.SearchParams(hnsw_ef=128, exact=False),
      limit=5
  )

  # 3️⃣ 유사한 문장들 처리
  clause_results = []
  for match in search_results.points:
    payload_data = match.payload or {}
    clause_results.append({
      "id": match.id,  # ✅ 벡터 ID
      "proof_text": payload_data.get("proof_text", ""),  # ✅ 원본 문장
      "incorrect_text": payload_data.get("incorrect_text", ""),  # ✅ 잘못된 문장
      "corrected_text": payload_data.get("corrected_text", "")  # ✅ 교정된 문장
    })

  # 4️⃣ 계약서 문장을 수정 (해당 조항의 TOP 5개 유사 문장을 기반으로)
  corrected_result = await prompt_service.correct_contract(
      clause_content=clause_content,
      proof_text=[item["proof_text"] for item in clause_results],  # 기준 문서들
      incorrect_text=[item["incorrect_text"] for item in clause_results],
      # 잘못된 문장들
      corrected_text=[item["corrected_text"] for item in clause_results]
      # 교정된 문장들
  )

  # 원문 텍스트에 대한 위치 정보 찾기
  positions = await find_text_positions(clause_content, pdf_document)

  position_values = []  # position_values를 저장할 리스트

  if positions:
    for position in positions:
      # 소수점 두 자리까지만 반올림
      page = position['page']
      bbox = position['bbox']

      # 각 좌표값을 소수점 두 자리까지 반올림
      rounded_bbox = [round(coord, 2) for coord in bbox]

      position_value = [page, rounded_bbox]
      position_values.append(position_value)  # position_values 리스트에 추가

  else:
    print("Text not found in the document.")

  # 최종 결과 저장
  rag_result.accuracy = corrected_result["accuracy"]
  rag_result.corrected_text = corrected_result["corrected_text"]
  rag_result.incorrect_text = corrected_result["clause_content"]  # 원본 문장
  rag_result.proof_text = corrected_result["proof_text"]
  rag_result.position = position_values  # 위치정보

  # accuracy가 0.5 이하일 경우 결과를 반환하지 않음
  if float(rag_result.accuracy) > 0.5:
    return rag_result
  else:
    return None  # accuracy가 0.5 이하일 경우 빈 객체 반환


async def find_text_positions(clause_content: str, pdf_document):
  positions = []  # 위치 정보를 저장할 리스트
  print(f'기존 문장 : {clause_content}')

  # 모든 페이지를 검색
  for page_num in range(pdf_document.page_count):
    page = pdf_document.load_page(page_num)  # 페이지 로드

    # 문장의 위치를 찾기 위해 search_for 사용
    text_instances = page.search_for(clause_content)

    # y값을 기준으로 묶을 변수
    grouped_positions = {}

    # 텍스트 인스턴스들에 대해 위치 정보를 추출
    for text_instance in text_instances:
      x0, y0, x1, y1 = text_instance  # 바운딩 박스 좌표

      # y 값을 기준으로 그룹화 (y0를 반올림하여 묶음)
      rounded_y = round(y0, 2)

      if rounded_y not in grouped_positions:
        grouped_positions[rounded_y] = []

      grouped_positions[rounded_y].append((x0, x1))

    # 그룹화된 바운딩 박스를 하나의 큰 박스로 묶기
    for y_key, group in grouped_positions.items():
      # 하나의 그룹에서 x0, x1의 최솟값과 최댓값을 구하기
      min_x0 = min([x[0] for x in group])  # 최소 x0 값
      max_x1 = max([x[1] for x in group])  # 최대 x1 값
      # 그룹에 해당하는 y 값은 동일하므로, 바운딩 박스를 만들 때 y0, y1은 동일
      positions.append({
        "page": page_num + 1,
        "bbox": (min_x0, y_key, max_x1, y_key + 16)
        # y1 값은 약간의 여유를 두고 설정 (필요시 조정)
      })

  return positions
