from typing import List, Tuple
from qdrant_client import models
from app.clients.qdrant_client import qdrant_db_client
from app.schemas.analysis_response import RagResult, AnalysisResponse
from app.schemas.chunk_schema import ArticleChunk
from app.schemas.document_request import DocumentRequest
from app.containers.service_container import embedding_service, prompt_service

def vectorize_and_calculate_similarity(chunks: List[ArticleChunk],
    pdf_request: DocumentRequest) -> Tuple[AnalysisResponse, int]:
  analysis_response = AnalysisResponse(
      summary="",
      total_page=0,
      chunks=[]
  )

  for article in chunks:

    for clause in article.clauses:
      if len(clause.clause_content) <= 1:
        continue

      clause_content = clause.clause_content

      # 1️⃣ OpenAI 벡터화
      clause_vector = embedding_service.embed_text(clause_content)

      # 2️⃣ Qdrant에서 유사한 벡터 검색 (query_points 사용)
      search_results = qdrant_db_client.query_points(
          collection_name="standard",
          query=clause_vector,  # 리스트 타입 확인 완료
          query_filter=models.Filter(
              must=[
                models.FieldCondition(
                    key="category",
                    match=models.MatchValue(value=pdf_request.categoryName)
                )
              ]
          ),
          search_params=models.SearchParams(hnsw_ef=128, exact=False),
          limit=5  # 최상위 5개 유사한 벡터 검색
      )

      # 5개의 문장별 검색 결과 저장 (현재 조항에 대한 유사한 문장들만 저장)
      rag_result = RagResult(clause_content=clause_content)

      for match in search_results.points:
        payload_data = match.payload or {}
        rag_result.proof_texts.append(payload_data.get("proof_text"))
        rag_result.incorrect_texts.append(payload_data.get("incorrect_text"))
        rag_result.corrected_texts.append(payload_data.get("corrected_text"))

      analysis_response.chunks.append(rag_result)

  return analysis_response, 200  # ✅ 최종 JSON 형태로 반환
