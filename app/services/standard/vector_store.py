import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import List

import numpy as np
from httpx import ConnectTimeout
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException

from qdrant_client.models import Distance, VectorParams, PointStruct

from app.blueprints.standard.standard_exception import StandardException
from app.clients.qdrant_client import get_qdrant_client
from app.common.constants import MAX_RETRIES
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.containers.service_container import embedding_service, prompt_service
from app.models.vector import VectorPayload
from app.schemas.document_request import DocumentRequest


async def vectorize_and_save(chunks: List[str],
    pdf_request: DocumentRequest) -> None:
  qd_client = get_qdrant_client()
  await ensure_qdrant_collection(qd_client, pdf_request.categoryName)

  start_time = time.perf_counter()
  embeddings = await embedding_service.batch_embed_texts(chunks)
  logging.info(f"임베딩 묶음 소요 시간: {time.perf_counter() - start_time:.4f}초")

  valid_inputs = [
    (article, vector)
    for article, vector in zip(chunks, embeddings)
    if(
        vector is not None or
        isinstance(vector, list) or
        not any(np.isnan(x) for x in vector)
    )
  ]

  tasks = [
    generate_point_from_clause(article, embedding, pdf_request)
    for article, embedding in valid_inputs
  ]

  # 비동기 실행
  results = await asyncio.gather(*tasks)

  # None 제거 후 업로드
  points = [point for point in results if point]
  await upload_points_to_qdrant(qd_client, pdf_request.categoryName, points)


async def generate_point_from_clause(article: str, embedding: List[float],
    pdf_request: DocumentRequest) -> PointStruct | None:

  result = await retry_make_correction(article)
  if not result:
    return None

  payload = VectorPayload(
      standard_id=pdf_request.id,
      incorrect_text=result.get("incorrect_text") or "",
      proof_text=article,
      corrected_text=result.get("corrected_text") or "",
      created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  )

  return PointStruct(
      id=str(uuid.uuid4()),
      vector=embedding,
      payload=payload.to_dict()
  )


async def retry_make_correction(clause_content: str) -> dict:
  for attempt in range(1, MAX_RETRIES + 1):
    result = await prompt_service.make_correction_data(clause_content)
    if result is not None:
      return result
    logging.warning(f"교정 응답 실패. 재시도 {attempt}/{MAX_RETRIES}")
  raise StandardException(ErrorCode.PROMPT_MAX_TRIAL_FAILED)


async def ensure_qdrant_collection(qd_client: AsyncQdrantClient,
    collection_name: str) -> None:
  try:
    exists = await qd_client.collection_exists(collection_name=collection_name)
    if not exists:
      await create_qdrant_collection(qd_client, collection_name)

  except (ConnectTimeout, ResponseHandlingException):
    raise CommonException(ErrorCode.QDRANT_NOT_STARTED)


async def create_qdrant_collection(qd_client: AsyncQdrantClient,
    collection_name: str):
  try:
    return await qd_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )
  except (ConnectTimeout, ResponseHandlingException):
    raise CommonException(ErrorCode.QDRANT_CONNECTION_TIMEOUT)


async def upload_points_to_qdrant(qd_client: AsyncQdrantClient, collection_name,
    points):
  if not points:
    raise StandardException(ErrorCode.NO_POINTS_GENERATED)

  try:
    await qd_client.upsert(collection_name=collection_name, points=points)
  except (ConnectTimeout, ResponseHandlingException):
    raise CommonException(ErrorCode.QDRANT_CONNECTION_TIMEOUT)
