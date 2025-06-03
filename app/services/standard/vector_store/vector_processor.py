import asyncio
import uuid
from typing import List

from qdrant_client.models import PointStruct

from app.blueprints.standard.standard_exception import StandardException
from app.clients.openai_clients import get_prompt_async_client, \
  get_dense_embedding_async_client
from app.clients.qdrant_client import get_qdrant_client
from app.common.decorators import async_measure_time
from app.common.exception.error_code import ErrorCode
from app.containers.service_container import embedding_service
from app.models.vector import VectorPayload
from app.schemas.chunk_schema import ClauseChunk
from app.schemas.document_request import DocumentRequest
from app.services.common.keyword_searcher import \
  get_sparse_embedding_async_client
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

  async with get_dense_embedding_async_client() as dense_client, \
      get_sparse_embedding_async_client() as sparse_client:
    dense_task = embedding_service.batch_embed_texts(dense_client,
                                                     embedding_inputs)
    sparse_task = embedding_service.batch_embed_texts_sparse(sparse_client,
                                                             embedding_inputs)
    dense_vectors, sparse_vectors = await asyncio.gather(dense_task,
                                                         sparse_task)

  final_points = []
  try:
    for payload, dense_vec, sparse_vec in zip(results, dense_vectors,
                                              sparse_vectors):
      if payload and dense_vec and sparse_vec:
        final_points.append(build_point(payload, {
          "dense": dense_vec,
          "sparse": sparse_vec
        }))
  except Exception:
    raise StandardException(ErrorCode.BUILD_POINT_FAILED)

  if await point_exists(qd_client, pdf_request.categoryName, pdf_request.id):
    await delete_by_standard_id(pdf_request.id, pdf_request.categoryName)

  await upload_points_to_qdrant(qd_client, pdf_request.categoryName,
                                final_points)


def build_point(payload: VectorPayload, vectors: dict) -> PointStruct:
  return PointStruct(
      id=uuid.uuid4().hex,
      vector={
        "dense": vectors["dense"],
        "sparse": vectors["sparse"],
      },
      payload=payload.to_dict()
  )
