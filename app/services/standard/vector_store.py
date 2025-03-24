import asyncio
import logging
import uuid
from datetime import datetime
from typing import List

from qdrant_client.models import Distance, VectorParams, PointStruct

from app.blueprints.standard.standard_exception import StandardException
from app.clients.qdrant_client import qdrant_db_client
from app.common.exception.error_code import ErrorCode
from app.containers.service_container import embedding_service, prompt_service, \
  text_service
from app.models.vector import VectorPayload
from app.schemas.chunk_schema import ArticleChunk, ClauseChunk
from app.schemas.document_request import DocumentRequest

MAX_RETRIES = 3
def vectorize_and_save(chunks: List[ArticleChunk], collection_name: str,
    pdf_request: DocumentRequest) -> None:
  points = []
  ensure_qdrant_collection(collection_name)

  for article in chunks:
    article_number = article.article_title

    if len(article.clauses) == 0:
      continue

    for clause in article.clauses:
      if len(clause.clause_content) <= 1:
        continue

      clause_content = clause.clause_content
      combined_text = f"조 {article_number}, 항 {clause.clause_number}: {clause_content}"

      # 1️⃣ Openai 벡터화
      clause_vector = embedding_service.embed_text(combined_text)

      result = None
      for attempt in range(1, MAX_RETRIES + 1):
        # 2️⃣ Openai LLM 기반 교정 문구 생성
        result = prompt_service.make_correction_data(clause_content)
        if result is not None:
          break
        logging.warning(f"교정 응답 실패. 재시도 {attempt}/{MAX_RETRIES}")

      if result is None:
        raise StandardException(ErrorCode.PROMPT_MAX_TRIAL_FAILED)

      payload = VectorPayload(
          standard_id=pdf_request.id,
          category=pdf_request.categoryName,
          incorrect_text=result["incorrect_text"],
          proof_text=clause_content,
          corrected_text=result["corrected_text"],
          created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      )

      points.append(
          PointStruct(
              id=str(uuid.uuid4()),
              vector=clause_vector,
              payload=payload.to_dict()
          )
      )

  upload_points_to_qdrant(collection_name, points)


async def vectorize_and_save_by_async_gpt(chunks: List[ArticleChunk],
    collection_name: str, pdf_request: DocumentRequest) -> None:
  ensure_qdrant_collection(collection_name)
  tasks = []

  for article in chunks:
    if len(article.clauses) == 0:
      continue

    for clause in article.clauses:
      tasks.append(process_clause(article.article_title, clause, pdf_request))

  # 비동기 실행
  results = await asyncio.gather(*tasks)

  # None 제거 후 업로드
  points = [point for point in results if point]
  upload_points_to_qdrant(collection_name, points)


async def process_clause(article_title: str, clause: ClauseChunk,
    pdf_request: DocumentRequest) -> PointStruct | None:
  if len(clause.clause_content) <= 1:
    return None

  clause_content = clause.clause_content
  combined_text = f"조 {article_title}, 항 {clause.clause_number}: {clause_content}"

  try:
    clause_vector, result = await asyncio.gather(
        text_service.embed_text_async_ver(combined_text),
        retry_make_correction(clause_content)
    )
  except StandardException:
    return None

  payload = VectorPayload(
      standard_id=pdf_request.id,
      category=pdf_request.categoryName,
      incorrect_text=result["incorrect_text"],
      proof_text=clause_content,
      corrected_text=result["corrected_text"],
      created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  )

  return PointStruct(
      id=str(uuid.uuid4()),
      vector=clause_vector,
      payload=payload.to_dict()
  )


async def retry_make_correction(clause_content: str) -> dict:
  for attempt in range(1, MAX_RETRIES + 1):
    result = await text_service.make_correction_data_async_ver(clause_content)
    if result is not None:
      return result
    logging.warning(f"교정 응답 실패. 재시도 {attempt}/{MAX_RETRIES}")
  raise StandardException(ErrorCode.PROMPT_MAX_TRIAL_FAILED)


async def vectorize_and_save_async_with_to_thread(chunks: List[ArticleChunk],
    collection_name: str,
    pdf_request: DocumentRequest):
  points = []
  ensure_qdrant_collection(collection_name)

  tasks = []
  for article in chunks:
    article_number = article.article_title

    if len(article.clauses) == 0:
      continue

    for clause in article.clauses:
      if len(clause.clause_content) <= 1:
        continue

      clause_content = clause.clause_content
      combined_text = f"조 {article_number}, 항 {clause.clause_number}: {clause_content}"

      # 1️⃣ OpenAI 벡터화 (동기 → 비동기 변환)
      embed_task = asyncio.to_thread(embedding_service.embed_text,
                                     combined_text)

      # 2️⃣ OpenAI LLM 기반 교정 문구 생성 (동기 → 비동기 변환)
      prompt_task = asyncio.to_thread(prompt_service.make_correction_data,
                                      clause_content)

      tasks.append(
          asyncio.gather(embed_task, prompt_task, return_exceptions=True))

  results = await asyncio.gather(*tasks)

  # 결과를 처리하고 Qdrant에 저장
  for (clause_vector, result), clause in zip(results, article.clauses):
    if isinstance(result, Exception) or isinstance(clause_vector, Exception):
      continue  # 에러 발생 시 스킵

    if result is None:
      result = {}  # ❗ None이면 get 호출 안 되니까 빈 dict로 처리

    payload = VectorPayload(
        standard_id=pdf_request.id,
        category=pdf_request.categoryName,
        incorrect_text=result.get("incorrect_text", ""),
        proof_text=clause.clause_content,
        corrected_text=result.get("corrected_text", ""),
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    points.append(
        PointStruct(
            id=str(uuid.uuid4()),
            vector=clause_vector,
            payload=payload.to_dict()
        )
    )

  # 최종 Qdrant 업로드
  upload_points_to_qdrant(collection_name, points)


def ensure_qdrant_collection(collection_name: str) -> None:
  exists = qdrant_db_client.collection_exists(collection_name=collection_name)
  if not exists:
    create_qdrant_collection(collection_name)


def create_qdrant_collection(collection_name: str):
  return qdrant_db_client.create_collection(
      collection_name=collection_name,
      vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
  )


def upload_points_to_qdrant(collection_name, points):
  if len(points) == 0:
    raise StandardException(ErrorCode.NO_POINTS_FOUND)
  qdrant_db_client.upsert(collection_name=collection_name, points=points)
