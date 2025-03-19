import logging
from typing import List
from qdrant_client import models
from app.clients.qdrant_client import qdrant_db_client
from app.schemas.chunk_schema import ArticleChunk
from app.schemas.document_request import DocumentRequest
from app.containers.service_container import embedding_service, prompt_service


def vectorize_and_calculate_similarity(chunks: List[ArticleChunk],
    pdf_request: DocumentRequest) -> List[dict]:
  results = []  # 최종 반환할 결과 저장

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
                    key="categoryName",
                    match=models.MatchValue(value=pdf_request.categoryName)
                )
              ]
          ),
          search_params=models.SearchParams(hnsw_ef=128, exact=False),
          limit=5  # 최상위 5개 유사한 벡터 검색
      )

      # 5개의 문장별 검색 결과 저장 (현재 조항에 대한 유사한 문장들만 저장)
      clause_results = []
      for match in search_results.points:
        payload_data = match.payload or {}

        clause_results.append({
          "id": match.id,  # ✅ 벡터 ID
          "proof_text": payload_data.get("proof_text", ""),  # ✅ 원본 문장
          "incorrect_text": payload_data.get("incorrect_text", ""),  # ✅ 잘못된 문장
          "corrected_text": payload_data.get("corrected_text", "")  # ✅ 교정된 문장
        })

      # 3️⃣ 계약서 문장을 수정 (해당 조항의 TOP 5개 유사 문장을 기반으로)
      corrected_result = prompt_service.correct_contract(
          clause_content=clause_content,  # 현재 계약서 문장
          proof_text=[item["proof_text"] for item in clause_results],  # 기준 문서들
          incorrect_texts=[item["incorrect_text"] for item in clause_results],  # 잘못된 문장들
          corrected_texts=[item["corrected_text"] for item in clause_results],  # 교정된 문장들
      )

      # 최종 결과 저장
      results.append({
        "incorrect_text": corrected_result["clause_content"],  # 원본 문장
        "corrected_text": corrected_result["corrected_text"],  # LLM이 교정한 문장
        "proof_text": corrected_result["proof_text"],  # 참고한 기준 문서
        "accuracy": corrected_result["accuracy"], # 신뢰도
      })

  logging.debug(f'타입 확인{type(results)}')
  logging.debug(f'값 확인{results}')

  return results  # ✅ 최종 JSON 형태로 반환
