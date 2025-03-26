import asyncio
from typing import List

from qdrant_client import models

from app.clients.qdrant_client import qdrant_db_client
from app.common.constants import Constants
from app.schemas.analysis_response import RagResult
from app.schemas.chunk_schema import DocumentChunk
from app.schemas.document_request import DocumentRequest
from app.containers.service_container import embedding_service, prompt_service
from app.services.standard.vector_store import ensure_qdrant_collection

async def vectorize_and_calculate_similarity(
    chunks: List[DocumentChunk], document_request: DocumentRequest) -> list:

  # 각 조항에 대해 비동기 태스크 생성
  tasks = []
  for article in chunks:
    tasks.append(process_clause(article.clause_content, document_request,
                                article.page, article.order_index))

  # 모든 임베딩 및 유사도 검색 태스크를 병렬로 실행
  results = await asyncio.gather(*tasks)

  # 반환 값에서 null 제거
  filtered_results = [result for result in results if result is not None]

  return filtered_results


async def process_clause(clause_content: str, document_request: DocumentRequest,
                          page: int, sentence_index: int):
  embedding = await embedding_service.embed_text(clause_content)

  # Qdrant에서 유사한 벡터 검색 (해당 호출이 동기라면 그대로 사용)
  search_results = await qdrant_db_client.query_points(
      collection_name=Constants.QDRANT_COLLECTION.value,
      query=embedding,
      query_filter=models.Filter(
          must=[
            models.FieldCondition(
                key="category",
                match=models.MatchValue(value=document_request.categoryName)
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
      incorrect_text=[item["incorrect_text"] for item in clause_results],  # 잘못된 문장들
      corrected_text=[item["corrected_text"] for item in clause_results]  # 교정된 문장들
  )


  # 최종 결과 저장
  result = {
      "incorrect_text": corrected_result["incorrect_text"],  # 원본 문장
      "corrected_text": corrected_result["corrected_text"],  # LLM이 교정한 문장
      "proof_text": corrected_result["proof_text"],  # 참고한 기준 문서
      "accuracy": corrected_result["accuracy"],  # 신뢰도
      "page": page,  # 페이지 번호
      "sentence_index": sentence_index  # 문장 인덱스
  }

  # accuracy가 0.5 이하일 경우 결과를 반환하지 않음
  if float(result["accuracy"]) > 0.5:
    return result
  else:
    return None  # accuracy가 0.5 이하일 경우 빈 객체 반환


async def vectorize_and_calculate_similarity2(
    document_chunks: List[DocumentChunk],
    collection_name: str, document_request: DocumentRequest) -> List[RagResult]:
  tasks = []
  await ensure_qdrant_collection(collection_name)
  for chunk in document_chunks:
    if len(chunk.clause_content) <= 1:
      continue
    rag_result = RagResult(
        page=chunk.page,
        order_index=chunk.order_index
    )
    task = process_clause2(
        rag_result, collection_name, chunk.clause_content,
        document_request.categoryName
    )
    tasks.append(task)

  # 모든 임베딩 및 유사도 검색 태스크를 병렬로 실행
  results = await asyncio.gather(*tasks)
  return [r for r in results if r is not None]


async def process_clause2(rag_result: RagResult, clause_content: str,
    collection_name: str, categoryName: str):
  embedding = await embedding_service.embed_text(clause_content)

  search_results = await qdrant_db_client.query_points(
      collection_name=collection_name,
      query=embedding,
      query_filter=models.Filter(
          must=[
            models.FieldCondition(
                key="category",
                match=models.MatchValue(value=categoryName)
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
      "proof_texts": payload_data.get("proof_texts", ""),  # ✅ 원본 문장
      "incorrect_text": payload_data.get("incorrect_text", ""),  # ✅ 잘못된 문장
      "corrected_text": payload_data.get("corrected_text", "")  # ✅ 교정된 문장
    })

  # 4️⃣ 계약서 문장을 수정 (해당 조항의 TOP 5개 유사 문장을 기반으로)
  corrected_result = await prompt_service.correct_contract(
      clause_content=clause_content,
      proof_texts=[item["proof_texts"] for item in clause_results],  # 기준 문서들
      incorrect_texts=[item["incorrect_text"] for item in clause_results],
      corrected_texts=[item["corrected_text"] for item in clause_results],
  )


  # 최종 결과 저장
  rag_result.accuracy = corrected_result["accuracy"]
  rag_result.corrected_text = corrected_result["corrected_text"]
  rag_result.incorrect_text = corrected_result["clause_content"]
  rag_result.proof_text = corrected_result["proof_text"]

  return rag_result