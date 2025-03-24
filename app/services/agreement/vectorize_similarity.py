import asyncio
from typing import List

from qdrant_client import models

from app.blueprints.agreement.agreement_exception import AgreementException
from app.clients.qdrant_client import qdrant_db_client
from app.common.constants import Constants
from app.common.exception.error_code import ErrorCode
from app.schemas.analysis_response import RagResult, AnalysisResponse
from app.schemas.chunk_schema import ArticleChunk
from app.schemas.document_request import DocumentRequest
from app.containers.service_container import text_service, prompt_service


async def vectorize_and_calculate_similarity(extracted_text: str,
    chunks: List[ArticleChunk], pdf_request: DocumentRequest) -> AnalysisResponse:
  analysis_response = AnalysisResponse(
      original_text=extracted_text,
      total_page=0,
      chunks=[]
  )

  # 각 조항에 대해 비동기 태스크 생성
  tasks = []
  for article in chunks:
    for clause in article.clauses:
      if len(clause.clause_content) <= 1:
        continue
      tasks.append(process_clause(clause.clause_content, pdf_request))

  # 모든 임베딩 및 유사도 검색 태스크를 병렬로 실행
  results = await asyncio.gather(*tasks)
  analysis_response.chunks.extend(results)

  return analysis_response


async def process_clause(clause_content: str, pdf_request: DocumentRequest):
  embedding = await text_service.embed_text_async_ver(clause_content)

  # Qdrant에서 유사한 벡터 검색 (해당 호출이 동기라면 그대로 사용)
  search_results = await qdrant_db_client.query_points(
      collection_name=Constants.QDRANT_COLLECTION.value,
      query=embedding,
      query_filter=models.Filter(
          must=[
            models.FieldCondition(
                key="category",
                match=models.MatchValue(value=pdf_request.categoryName)
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
      incorrect_texts=[item["incorrect_text"] for item in clause_results],  # 잘못된 문장들
      corrected_texts=[item["corrected_text"] for item in clause_results],  # 교정된 문장들
  )

  # 최종 결과 저장
  return {
      "incorrect_text": corrected_result["clause_content"],  # 원본 문장
      "corrected_text": corrected_result["corrected_text"],  # LLM이 교정한 문장
      "proof_text": corrected_result["proof_text"],  # 참고한 기준 문서
      "accuracy": corrected_result["accuracy"]  # 신뢰도
  }

