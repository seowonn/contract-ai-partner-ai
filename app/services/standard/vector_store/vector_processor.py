import asyncio
import uuid
from typing import List

import numpy as np
from qdrant_client.models import PointStruct

from app.clients.openai_clients import get_prompt_async_client, \
  get_embedding_async_client
from app.clients.qdrant_client import get_qdrant_client
from app.common.decorators import async_measure_time
from app.containers.service_container import embedding_service
from app.schemas.chunk_schema import ClauseChunk
from app.schemas.document_request import DocumentRequest
from app.services.common.qdrant_utils import ensure_qdrant_collection, \
  upload_points_to_qdrant, point_exists
from app.services.standard.vector_delete import delete_by_standard_id
from app.services.standard.vector_store.payload_builder import \
  make_clause_payload


@async_measure_time
async def vectorize_and_save(chunks: List[ClauseChunk],
    pdf_request: DocumentRequest) -> None:
  qd_client = get_qdrant_client()
  await ensure_qdrant_collection(qd_client, pdf_request.categoryName)

  semaphore = asyncio.Semaphore(5)
  async with get_prompt_async_client() as prompt_client:
    results = await asyncio.gather(*[
      make_clause_payload(prompt_client, article, pdf_request, semaphore)
      for article in chunks
    ])

  embedding_inputs = [point.embedding_input() for point in results if point]

  async with get_embedding_async_client() as embedding_client:
    embeddings = await embedding_service.batch_embed_texts(embedding_client,
                                                           embedding_inputs)

  final_points = []
  for payload, vector in zip(results, embeddings):
    if vector and isinstance(vector, list) and not any(
        np.isnan(x) for x in vector):
      final_points.append(build_point(payload, vector))

  if await point_exists(qd_client, pdf_request.categoryName, pdf_request.id):
    await delete_by_standard_id(pdf_request.id, pdf_request.categoryName)

  await upload_points_to_qdrant(qd_client, pdf_request.categoryName,
                                final_points)


def build_point(payload, embedding: List[float]) -> PointStruct:
  return PointStruct(
      id=str(uuid.uuid4()),
      vector=embedding,
      payload=payload.to_dict()
  )
