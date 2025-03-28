import asyncio
from typing import List

from httpx import ConnectTimeout
from qdrant_client import models
from qdrant_client.http.exceptions import ResponseHandlingException

from app.clients.qdrant_client import get_qdrant_client
from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode
from app.schemas.analysis_response import RagResult
from app.schemas.document_request import DocumentRequest
from app.containers.service_container import embedding_service, prompt_service
from app.services.standard.vector_store import ensure_qdrant_collection

async def vectorize_and_calculate_similarity(
    sorted_chunks: List[RagResult],
    collection_name: str, document_request: DocumentRequest) -> List[RagResult]:

  await ensure_qdrant_collection(collection_name)

  tasks = []
  for chunk in sorted_chunks:
    tasks.append(process_clause(chunk, chunk.incorrect_text,
                                collection_name, document_request.categoryName))

  # 모든 임베딩 및 유사도 검색 태스크를 병렬로 실행
  results = await asyncio.gather(*tasks)
  return [result for result in results if result is not None]


async def process_clause(rag_result: RagResult, clause_content: str,
    collection_name: str, category_name: str):
  embedding = await embedding_service.embed_text(clause_content)

  try:
    client = get_qdrant_client()
    search_results = await client.query_points(
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
  except (ConnectTimeout, ResponseHandlingException):
    raise BaseCustomException(ErrorCode.QDRANT_CONNECTION_TIMEOUT)

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
      incorrect_text=[item["incorrect_text"] for item in clause_results],  # 잘못된 문장들
      corrected_text=[item["corrected_text"] for item in clause_results]  # 교정된 문장들
  )

  # 최종 결과 저장
  rag_result.accuracy = float(corrected_result["accuracy"])
  rag_result.corrected_text = corrected_result["corrected_text"]
  rag_result.incorrect_text = corrected_result["clause_content"]
  rag_result.proof_text = corrected_result["proof_text"]

  # accuracy가 0.5 이하일 경우 결과를 반환하지 않음
  if rag_result.accuracy > 0.5:
    # rag_result.clause_data.position = 여기를 채우시오
    return rag_result
  else:
    return None  # accuracy가 0.5 이하일 경우 빈 객체 반환