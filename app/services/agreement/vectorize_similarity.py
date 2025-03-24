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
from app.containers.service_container import embedding_service


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


async def process_clause(clause_content: str, pdf_request: DocumentRequest) -> RagResult:
  # 텍스트 임베딩을 별도 스레드에서 실행 (blocking call을 비동기로 전환)
  embedding = await asyncio.to_thread(embedding_service.embed_text,
                                      clause_content)

  # Qdrant에서 유사한 벡터 검색 (해당 호출이 동기라면 그대로 사용)
  search_results = qdrant_db_client.query_points(
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

  if len(search_results.points) == 0:
    raise AgreementException(ErrorCode.NO_SEARCH_RESULT)

  # 5개의 문장별 검색 결과 저장 (현재 조항에 대한 유사한 문장들만 저장)
  rag_result = RagResult(clause_content=clause_content)
  for match in search_results.points:
    payload_data = match.payload or {}
    rag_result.proof_texts.append(payload_data.get("proof_text"))
    rag_result.incorrect_texts.append(payload_data.get("incorrect_text"))
    rag_result.corrected_texts.append(payload_data.get("corrected_text"))
  return rag_result