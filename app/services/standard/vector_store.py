import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import List

import numpy as np
from httpx import ConnectTimeout
from openai import AsyncAzureOpenAI
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException

from qdrant_client.models import Distance, VectorParams, PointStruct

from app.blueprints.standard.standard_exception import StandardException
from app.clients.openai_clients import get_prompt_async_client, \
  get_embedding_async_client
from app.clients.qdrant_client import get_qdrant_client
from app.common.constants import MAX_RETRIES, LLM_TIMEOUT
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.containers.service_container import embedding_service, prompt_service
from app.models.vector import VectorPayload, WordPayload
from app.schemas.chunk_schema import ClauseChunk
from app.schemas.document_request import DocumentRequest

STANDARD_LLM_REQUIRED_KEYS = {"incorrect_text", "corrected_text"}


async def vectorize_and_save(chunks: List[ClauseChunk],
    pdf_request: DocumentRequest) -> None:
  qd_client = get_qdrant_client()
  await ensure_qdrant_collection(qd_client, pdf_request.categoryName)

  semaphore = asyncio.Semaphore(5)
  async with get_prompt_async_client() as prompt_client:
    if pdf_request.categoryName == "법률용어":
      task_fn = make_word_payload
    else:
      task_fn = make_clause_payload

    results = await asyncio.gather(*[
      task_fn(prompt_client, article, pdf_request, semaphore)
      for article in chunks
    ])

  embedding_inputs = [point.embedding_input() for point in results if point]

  async with get_embedding_async_client() as embedding_client:
    start_time = time.perf_counter()
    embeddings = await embedding_service.batch_embed_texts(embedding_client,
                                                           embedding_inputs)
    logging.info(f"임베딩 묶음 소요 시간: {time.perf_counter() - start_time:.4f}초")

  final_points = []
  for payload, vector in zip(results, embeddings):
    if vector and isinstance(vector, list) and not any(
        np.isnan(x) for x in vector):
      final_points.append(build_point(payload, vector))

  await upload_points_to_qdrant(qd_client, pdf_request.categoryName,
                                final_points)


async def make_clause_payload(prompt_client, article, pdf_request,
    semaphore) -> VectorPayload | None:
  async with semaphore:
    result = await retry_make_correction(prompt_client, article)
    if not result:
      return None

  return VectorPayload(
      standard_id=pdf_request.id,
      incorrect_text=result.get("incorrect_text") or "",
      proof_text=article.clause_content,
      corrected_text=result.get("corrected_text") or "",
      created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  )


async def make_word_payload(prompt_client, article: ClauseChunk, pdf_request,
    semaphore) -> WordPayload | None:
  async with semaphore:
    result = await prompt_service.extract_keywords(prompt_client, article)
    if (
        not result or
        not isinstance(result, dict) or
        "keyword" not in result or
        not isinstance(result["keyword"], list)
    ):
      return None

  return WordPayload(
      standard_id=pdf_request.id,
      term=article.clause_number,
      original_text=article.clause_content,
      keywords=result["keyword"],
      created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  )


def build_point(payload, embedding: List[float]) -> PointStruct:
  return PointStruct(
      id=str(uuid.uuid4()),
      vector=embedding,
      payload=payload.to_dict()
  )


async def retry_make_correction(prompt_client: AsyncAzureOpenAI,
    clause_content: str) -> dict:
  for attempt in range(1, MAX_RETRIES + 1):
    try:
      result = await asyncio.wait_for(
          prompt_service.make_correction_data(prompt_client, clause_content),
          timeout=LLM_TIMEOUT
      )
      if isinstance(result, dict) and STANDARD_LLM_REQUIRED_KEYS.issubset(
          result.keys()):
        return result
      logging.warning(f"[retry_make_correction]: llm 응답 필수 키 누락됨")

    except Exception as e:
      if isinstance(e, asyncio.TimeoutError):
        if attempt == MAX_RETRIES:
          raise CommonException(ErrorCode.LLM_RESPONSE_TIMEOUT)

      else:
        if attempt == MAX_RETRIES:
          raise StandardException(ErrorCode.STANDARD_REVIEW_FAIL)
        logging.warning(
            f"[retry_make_correction]: 기준 문서 LLM 재요청 발생 {attempt}/{MAX_RETRIES} {e}"
        )

      if attempt < MAX_RETRIES:
        await asyncio.sleep(0.5 * attempt)

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
