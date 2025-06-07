import asyncio
import logging
from asyncio import Semaphore
from typing import List, Optional, Any

import fitz
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Prefetch
from qdrant_client.models import FusionQuery, Fusion
from qdrant_client.models import QueryResponse, SparseVector

from app.blueprints.agreement.agreement_exception import AgreementException
from app.clients.openai_clients import get_prompt_async_client, \
  get_dense_embedding_async_client
from app.clients.qdrant_client import get_qdrant_client
from app.common.chunk_status import ChunkProcessResult, ChunkProcessStatus
from app.common.constants import CLAUSE_TEXT_SEPARATOR, MAX_RETRIES
from app.common.decorators import async_measure_time
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode
from app.containers.service_container import embedding_service, prompt_service
from app.schemas.analysis_response import RagResult, SearchResult
from app.schemas.document_request import DocumentRequest
from app.services.common.keyword_searcher import \
  get_sparse_embedding_async_client
from app.services.common.llm_retry import retry_llm_call
from app.services.common.qdrant_utils import ensure_qdrant_collection

SEARCH_COUNT = 3
VIOLATION_THRESHOLD = 0.85

LLM_REQUIRED_KEYS = {"clause_content", "correctedText", "proofText",
                     "violation_score"}


@async_measure_time
async def vectorize_and_calculate_similarity(
    document_chunks: List[RagResult], document_request: DocumentRequest,
    byte_type_pdf: fitz.Document) -> List[RagResult]:
  qd_client = get_qdrant_client()
  await ensure_qdrant_collection(qd_client, document_request.categoryName)

  embedding_inputs = await prepare_embedding_inputs(document_chunks)

  async with get_dense_embedding_async_client() as dense_client, \
      get_sparse_embedding_async_client() as sparse_client:
    dense_task = embedding_service.batch_embed_texts(dense_client,
                                                     embedding_inputs)
    sparse_task = embedding_service.batch_embed_texts_sparse(sparse_client,
                                                             embedding_inputs)
    dense_vectors, sparse_vectors = await asyncio.gather(dense_task,
                                                         sparse_task)

  # ✅ 세마포어 외부로 이동하여 task 재사용성 향상
  semaphore = Semaphore(5)
  tasks = [
    process_clause(qd_client, chunk, dense_vec, sparse_vec,
                   document_request.categoryName, byte_type_pdf, semaphore)
    for chunk, dense_vec, sparse_vec in
    zip(document_chunks, dense_vectors, sparse_vectors)
  ]
  results = await asyncio.gather(*tasks)

  success_results = [r.result for r in results if
                     r.status == ChunkProcessStatus.SUCCESS and r.result]

  failure_score = sum(r.status == ChunkProcessStatus.FAILURE for r in results)

  if not success_results and failure_score == len(document_chunks):
    raise AgreementException(ErrorCode.CHUNK_ANALYSIS_FAILED)

  return success_results


async def prepare_embedding_inputs(chunks: List[RagResult]) -> List[str]:
  inputs = []
  for chunk in chunks:
    inputs.append(f"{chunk.incorrect_text}")
  return inputs


async def process_clause(qd_client: AsyncQdrantClient, rag_result: RagResult,
    dense_vec: List[float], sparse_vec: SparseVector,
    collection_name: str, byte_type_pdf: fitz.Document,
    semaphore: Semaphore) -> ChunkProcessResult:
  search_results = await search_qdrant(semaphore, collection_name, dense_vec,
                                       sparse_vec,
                                       qd_client)
  parse_incorrect_text(rag_result)

  async with get_prompt_async_client() as prompt_client:
    corrected_result = await retry_llm_call(
        prompt_service.correct_contract,
        prompt_client, rag_result.incorrect_text.replace("\n", " "),
        search_results,
        required_keys=LLM_REQUIRED_KEYS
    )
  if not corrected_result:
    return ChunkProcessResult(status=ChunkProcessStatus.FAILURE)

  try:
    score = float(corrected_result["violation_score"])
  except (KeyError, ValueError, TypeError):
    logging.warning(f"violation_score 추출 실패")
    return ChunkProcessResult(status=ChunkProcessStatus.FAILURE)

  if score < VIOLATION_THRESHOLD:
    return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS)

  incorrect_part = corrected_result["incorrectPart"]

  all_positions, part_position = \
    await find_text_positions(rag_result, incorrect_part, byte_type_pdf)

  rag_result.accuracy = score
  positions = await extract_positions_by_page(all_positions)
  part_positions = await extract_positions_by_page(part_position)

  set_result_data(corrected_result, rag_result, positions, part_positions)
  if any(not clause.position for clause in rag_result.clause_data):
    logging.warning(f"원문 일치 position값 불러오지 못함")
    return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS)

  return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS,
                            result=rag_result)


def parse_incorrect_text(rag_result: RagResult) -> None:
  try:
    rag_result.incorrect_text = rag_result.incorrect_text.replace("\n", " ")
  except Exception:
    raise AgreementException(ErrorCode.NO_SEPARATOR_FOUND)


async def search_qdrant(semaphore: Semaphore, collection_name: str,
    dense_vec: List[float], sparse_vec: SparseVector,
    qd_client: AsyncQdrantClient) -> List[SearchResult]:
  search_results = await search_collection(qd_client, semaphore,
                                           collection_name, dense_vec,
                                           sparse_vec)
  return gather_search_results(search_results)


async def search_collection(qd_client: AsyncQdrantClient,
    semaphore: Semaphore, collection_name: str,
    dense_vec: List[float], sparse_vec: SparseVector) -> QueryResponse:
  for attempt in range(1, MAX_RETRIES + 1):
    try:
      async with semaphore:
        search_results = await qd_client.query_points(
            collection_name=collection_name,
            prefetch=[
              Prefetch(query=sparse_vec, using="sparse", limit=10),
              Prefetch(query=dense_vec, using="dense", limit=10),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=SEARCH_COUNT,
            with_payload=True
        )
        break

    except Exception as e:
      if attempt == MAX_RETRIES:
        raise CommonException(ErrorCode.QDRANT_SEARCH_FAILED)
      logging.warning(
          f"[search_collection]: Qdrant Search 재요청 발생 {attempt}/{MAX_RETRIES} {e}")
      await asyncio.sleep(1)

  if search_results is None or not search_results.points:
    raise AgreementException(ErrorCode.NO_POINTS_FOUND)

  return search_results


def gather_search_results(search_results: QueryResponse) -> List[SearchResult]:
  return [
    SearchResult(
        proof_text=point.payload.get("proof_text", ""),
        incorrect_text=point.payload.get("incorrect_text", ""),
        corrected_text=point.payload.get("corrected_text", ""),
        term_explanation=point.payload.get("term_explanation", "")
    )
    for point in search_results.points[:SEARCH_COUNT]
  ]


def is_correct_response_format(result: dict[str, str]) -> bool:
  return (
      isinstance(result, dict)
      and LLM_REQUIRED_KEYS.issubset(result.keys())
      and all(isinstance(result[key], str) for key in LLM_REQUIRED_KEYS)
  )


def set_result_data(corrected_result: Optional[
  dict[str, Any]], rag_result: RagResult, positions: List[List],
    part_positions: List[List]):
  rag_result.incorrect_text = (
    rag_result.incorrect_text.replace(CLAUSE_TEXT_SEPARATOR, "")
    .replace("\n", "")
    .replace("", '"')
  )

  value = corrected_result["correctedText"]
  rag_result.corrected_text = " ".join(value) if isinstance(value,
                                                            list) else value
  value = corrected_result["proofText"]
  rag_result.proof_text = " ".join(value) if isinstance(value, list) else value

  rag_result.clause_data[0].position = positions[0]
  if positions[1]:
    rag_result.clause_data[1].position = positions[1]

  rag_result.clause_data[0].position_part = part_positions[0]
  if positions[1]:
    rag_result.clause_data[1].position_part = part_positions[1]


def search_text_in_pdf(text: str, pdf_doc: fitz.Document, clause_data,
    is_relative=True) -> dict[int, List[dict]]:
  positions_by_page = {}
  # 페이지별 검색
  for clause_part in clause_data:
    page_num = clause_part.page
    page = pdf_doc.load_page(page_num - 1)

    page_width = float(page.rect.width)
    page_height = float(page.rect.height)

    page_positions = []

    # 바로 검색
    text_instances = page.search_for(text.strip())
    grouped_positions = {}

    for inst in text_instances:
      x0, y0, x1, y1 = inst

      # 상대값 또는 절대값으로 처리
      if is_relative:
        rel_x0 = x0 / page_width
        rel_y0 = y0 / page_height
        rel_x1 = x1 / page_width
        rel_y1 = y1 / page_height
      else:
        rel_x0, rel_y0, rel_x1, rel_y1 = x0, y0, x1, y1

      if rel_y0 not in grouped_positions:
        grouped_positions[rel_y0] = []

      grouped_positions[rel_y0].append((rel_x0, rel_x1, rel_y0, rel_y1))

    for y_key, group in grouped_positions.items():
      min_x0 = min(x[0] for x in group)
      max_x1 = max(x[1] for x in group)
      min_y0 = min(x[2] for x in group)
      max_y1 = max(x[3] for x in group)

      # 상대값이면 100배
      if is_relative:
        min_x0 *= 100
        min_y0 *= 100
        max_x1 *= 100
        max_y1 *= 100

      width = max_x1 - min_x0
      height = max_y1 - min_y0

      # 바운딩 박스를 생성 (최소값과 최대값을 사용)
      page_positions.append({
        "page": page_num,
        "bbox": (min_x0, min_y0, width, height)
      })

    if page_positions:
      positions_by_page[page_num] = page_positions

  return positions_by_page


async def find_text_positions(rag_result: RagResult, incorrect_part: str,
    pdf_document: fitz.Document) -> dict[str, dict[int, List[dict]]]:
  # incorrect_text 처리 (all_positions 용)
  clause_content_parts = rag_result.incorrect_text.split('+', 1)
  if len(clause_content_parts) > 1:
    rag_result.incorrect_text = clause_content_parts[1].strip()

  clause_parts = rag_result.incorrect_text.split('!!!')

  # 전체 문장 기준으로 검색
  all_positions = {}
  part_positions = {}
  for part in clause_parts:
    part = part.strip()
    if part == "":
      continue
    partial_result = search_text_in_pdf(part, pdf_document,
                                        rag_result.clause_data)
    for page, boxes in partial_result.items():
      if page not in all_positions:
        all_positions[page] = []
      all_positions[page].extend(boxes)

  # incorrect_part는 그대로 검색
  part_position = search_text_in_pdf(incorrect_part, pdf_document,
                                     rag_result.clause_data)
  for page, boxes in part_position.items():
    if page not in part_positions:
      part_positions[page] = []
    part_positions[page].extend(boxes)

  return all_positions, part_positions


async def extract_positions_by_page(all_positions: dict[int, List[dict]]) -> \
    List[List]:
  positions = [[], []]
  first_page = None

  # `rag_result.clause_data`에 두 개만 저장
  for page_num, positions_in_page in all_positions.items():
    # 첫 번째 문장이 시작되는 페이지를 찾으면 첫 번째 위치에 저장
    if first_page is None:
      first_page = page_num
      positions[0].extend(p['bbox'] for p in positions_in_page)
    else:
      # 첫 번째 문장이 시작된 후, 페이지가 변경되면 두 번째 위치에 저장
      if page_num != first_page:
        positions[1].extend(p['bbox'] for p in positions_in_page)

  return positions
