import asyncio
import json
import logging
import os
import re
import time
import uuid
from typing import List, Tuple

import cv2
import numpy as np
import requests
from dotenv import load_dotenv
from qdrant_client import AsyncQdrantClient

from app.blueprints.agreement.agreement_exception import AgreementException
from app.clients.openai_clients import get_embedding_async_client, \
  get_prompt_async_client
from app.clients.qdrant_client import get_qdrant_client
from app.common.chunk_status import ChunkProcessStatus, ChunkProcessResult
from app.common.constants import ARTICLE_OCR_HEADER_PATTERN
from app.common.exception.error_code import ErrorCode
from app.containers.service_container import embedding_service, prompt_service
from app.schemas.analysis_response import RagResult
from app.schemas.chunk_schema import DocumentChunk
from app.schemas.document_request import DocumentRequest
from app.services.agreement.vectorize_similarity import \
  prepare_embedding_inputs, search_qdrant, parse_incorrect_text, \
  LLM_REQUIRED_KEYS, VIOLATION_THRESHOLD
from app.services.common.chunking_service import MIN_CLAUSE_BODY_LENGTH, \
  get_clause_pattern, split_text_by_pattern
from app.services.common.llm_retry import retry_llm_call
from app.services.common.qdrant_utils import ensure_qdrant_collection

# .env 파일에서 환경변수 불러오기
load_dotenv()

NAVER_CLOVA_API_URL = os.getenv("NAVER_CLOVA_API_URL")
NAVER_CLOVA_API_KEY = os.getenv("NAVER_CLOVA_API_KEY")


def chunk_preamble_content_ocr(page_text: str, chunks: List[DocumentChunk],
    order_index: int) -> Tuple[int, List[DocumentChunk]]:
  first_article_match = (
    re.search(ARTICLE_OCR_HEADER_PATTERN, page_text, flags=re.MULTILINE))

  preamble = page_text[
             first_article_match.start():] if first_article_match else page_text
  return append_preamble_ocr(chunks, preamble, order_index)


def append_preamble_ocr(result: List[DocumentChunk], preamble: str,
    order_index: int) -> Tuple[int, List[DocumentChunk]]:
  pattern = get_clause_pattern(result[-1].clause_number)

  if not pattern:
    result.append(DocumentChunk(
        clause_content=preamble,
        order_index=order_index,
        clause_number=result[-1].clause_number
    ))
    return order_index + 1, result

  clause_chunks = split_text_by_pattern(preamble, pattern)
  lines = clause_chunks[0].strip().splitlines()
  content_lines = [line for line in lines if not line.strip().startswith("페이지")]

  result.append(DocumentChunk(
      clause_content="\n".join(content_lines),
      order_index=order_index,
      clause_number=result[-1].clause_number
  ))
  order_index += 1

  for j in range(1, len(clause_chunks), 2):
    clause_number = clause_chunks[j].strip()
    clause_content = clause_chunks[j + 1].strip() if j + 1 < len(
        clause_chunks) else ""

    if len(clause_content) >= MIN_CLAUSE_BODY_LENGTH:
      prev_clause_prefix = result[-1].clause_number.split(" ")[0]
      result.append(DocumentChunk(
          clause_content=clause_content,
          order_index=order_index,
          clause_number=f"{prev_clause_prefix} {clause_number}항"
      ))
      order_index += 1

  return order_index, result


def extract_ocr(image_url: str) -> Tuple[str, List[dict]]:
  logging.info(f"image_url: {image_url}")
  # URL에서 이미지를 다운로드

  logging.info(f"NAVER_CLOVA_API_URL: {NAVER_CLOVA_API_URL}")
  logging.info(f"NAVER_CLOVA_API_KEY: {NAVER_CLOVA_API_KEY}")

  image_response = requests.get(image_url)
  image_data = image_response.content
  logging.info(f"image_response: {image_response}")

  # 이미지 열기 (바이너리로 읽은 데이터를 사용)

  image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)

  # 1. 해상도 가로 세로 1/2 => 총 1/4 조정
  height, width = image.shape[:2]
  resize_ratio = 1
  resized_image = cv2.resize(image, (
  int(width * resize_ratio), int(height * resize_ratio)),
                             interpolation=cv2.INTER_LINEAR)

  # 2. 그레이스케일 변환
  gray = cv2.cvtColor(resized_image, cv2.COLOR_BGR2GRAY)

  # 3. 이진화 (OTSU : 자동으로 최적의 Thresholding)
  _, binarized_img = cv2.threshold(gray, 0, 255,
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)

  # OCR 요청 JSON 생성

  request_json = {
    'images': [
      {
        'format': 'jpg',
        'name': 'demo',  # 요청 이름
        # 'rotate': True
      }
    ],
    'requestId': str(uuid.uuid4()),
    'version': 'V2',
    'timestamp': int(round(time.time() * 1000))
  }


  payload = {'message': json.dumps(request_json).encode('UTF-8')}

  # 전송을 위한 인코딩
  files = [
    ('file', (
    'photo1_binary_low.jpg', cv2.imencode('.jpg', binarized_img)[1].tobytes(),
    'image/jpeg'))  # 이진화된 이미지를 바이너리로 전송
  ]
  headers = {
    'X-OCR-SECRET': NAVER_CLOVA_API_KEY
  }
  logging.info(f"headers: {headers}")
  logging.info(f"payload: {payload}")

  try:
    response = requests.request("POST", NAVER_CLOVA_API_URL, headers=headers, data=payload,
                              files=files)
  except Exception:
    raise AgreementException(ErrorCode.NAVER_OCR_REQUEST_FAIL)

  ocr_results = json.loads(response.text)

  image_height, image_width = binarized_img.shape[:2]

  all_texts_with_bounding_boxes = []
  full_text = ""
  current_idx = 0

  # OCR 결과에서 텍스트와 바운딩 박스를 묶어서 리스트로 저장
  for image_result in ocr_results['images']:
    for field in image_result['fields']:
      text = field['inferText']
      bounding_box = field['boundingPoly']['vertices']

      # 상대 좌표 변환
      relative_bounding_box = [
        {
          'x': vertex['x'] / image_width,
          'y': vertex['y'] / image_height
        }
        for vertex in bounding_box
      ]

      start_idx = current_idx
      end_idx = start_idx + len(text)

      # 텍스트 인덱스와 바운딩 박스를 함께 저장
      all_texts_with_bounding_boxes.append({
        'text': text,
        'bounding_box': relative_bounding_box,
        'start_idx': start_idx,
        'end_idx': end_idx
      })

      # full_text와 current_idx 갱신
      full_text += text + " "
      current_idx = len(full_text)

  return full_text, all_texts_with_bounding_boxes



async def vectorize_and_calculate_similarity_ocr(
    combined_chunks: List[RagResult], document_request: DocumentRequest,
    all_texts_with_bounding_boxes: List[dict]) -> List[RagResult]:
  qd_client = get_qdrant_client()
  await ensure_qdrant_collection(qd_client, document_request.categoryName)

  embedding_inputs = await prepare_embedding_inputs(combined_chunks)

  async with get_embedding_async_client() as embedding_client:
    embeddings = await embedding_service.batch_embed_texts(
        embedding_client, embedding_inputs)

  tasks = [
    process_clause_ocr(qd_client, chunk, embedding,
                       document_request.categoryName,
                       all_texts_with_bounding_boxes)
    for chunk, embedding in zip(combined_chunks, embeddings)
  ]
  results = await asyncio.gather(*tasks)

  success_results: List[RagResult] = [r.result for r in results if
                                      r.status == ChunkProcessStatus.SUCCESS and r.result is not None]
  failure_score = sum(r.status == ChunkProcessStatus.FAILURE for r in results)

  if not success_results and failure_score == len(combined_chunks):
    raise AgreementException(ErrorCode.CHUNK_ANALYSIS_FAILED)

  return success_results


async def process_clause_ocr(qd_client: AsyncQdrantClient,
    rag_result: RagResult, embedding: List[float], collection_name: str,
    all_texts_with_bounding_boxes: List[dict]) -> ChunkProcessResult:
  semaphore = asyncio.Semaphore(5)
  search_results = await search_qdrant(semaphore, collection_name, embedding,
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
    await find_text_positions_ocr(rag_result, incorrect_part,
                                  all_texts_with_bounding_boxes)

  rag_result.accuracy = score
  rag_result.corrected_text = corrected_result["correctedText"]
  rag_result.proof_text = corrected_result["proofText"]

  rag_result.clause_data[0].position.extend(all_positions)
  rag_result.clause_data[0].position_part.extend(part_position)

  if any(not clause.position for clause in rag_result.clause_data):
    logging.warning(f"원문 일치 position값 불러오지 못함")
    return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS)

  return ChunkProcessResult(status=ChunkProcessStatus.SUCCESS,
                            result=rag_result)


async def find_text_positions_ocr(rag_result: RagResult, incorrect_part: str,
    all_texts_with_bounding_boxes: List[dict]) -> tuple[
  List[tuple], List[tuple]]:
  # +를 기준으로 문장을 나누고 뒤에 있는 부분만 사용
  clause_content = rag_result.incorrect_text.split('+', 1)
  if len(clause_content) > 1:
    rag_result.incorrect_text = clause_content[1].strip()

  # +를 기준으로 문장을 나누고 뒤에 있는 부분만 사용
  part_clause_content = incorrect_part.split('+', 1)
  if len(part_clause_content) > 1:
    incorrect_part = part_clause_content[1].strip()

  all_positions, part_positions = extract_bbox_positions(
    rag_result.incorrect_text,
    incorrect_part,
    all_texts_with_bounding_boxes)

  return all_positions, part_positions



def extract_bbox_positions(
    clause_content: str,
    incorrect_part: str,
    all_texts_with_bounding_boxes: List[dict]
) -> tuple[List[tuple], List[tuple]]:
  full_text = " ".join(item['text'] for item in all_texts_with_bounding_boxes)

  def get_position_range(target_text: str, base_start: int = 0) -> tuple[
    int, int]:
    start_idx = full_text.find(target_text, base_start)
    end_idx = start_idx + len(target_text) if start_idx != -1 else -1
    return start_idx, end_idx

  def extract_bboxes(start_idx: int, end_idx: int) -> List[tuple]:
    epsilon = None

    matched_items = [
      item for item in all_texts_with_bounding_boxes
      if start_idx <= item['start_idx'] < end_idx
    ]

    grouped_texts = {}
    for item in matched_items:
      bounding_box = item['bounding_box']
      center_y = sum(vertex['y'] for vertex in bounding_box) / len(bounding_box)

      if epsilon is None:
        y_values = [vertex['y'] for vertex in bounding_box]
        group_height = max(y_values) - min(y_values)
        epsilon = group_height * 0.5

      abs_center_y = center_y
      group_found = False
      for y_group in grouped_texts:
        if y_group - epsilon < abs_center_y < y_group + epsilon:
          grouped_texts[y_group].append(item)
          group_found = True
          break
      if not group_found:
        grouped_texts[abs_center_y] = [item]

    points_list = []
    unique_relative_points = set()
    for y_group in grouped_texts:
      min_x_group = float('inf')
      min_y_group = float('inf')
      max_x_group = float('-inf')
      max_y_group = float('-inf')

      for item in grouped_texts[y_group]:
        for vertex in item['bounding_box']:
          abs_x = vertex['x']
          abs_y = vertex['y']
          min_x_group = min(min_x_group, abs_x)
          min_y_group = min(min_y_group, abs_y)
          max_x_group = max(max_x_group, abs_x)
          max_y_group = max(max_y_group, abs_y)

      min_x = min_x_group * 100
      min_y = min_y_group * 100
      width = (max_x_group - min_x_group) * 100
      height = (max_y_group - min_y_group) * 100

      points_tuple = (min_x, min_y, width, height)
      if points_tuple not in unique_relative_points:
        unique_relative_points.add(points_tuple)
        points_list.append(points_tuple)

    return points_list

  # 전체 문장 기준
  clause_start_idx, clause_end_idx = get_position_range(clause_content)
  # 부분 문장은 전체 문장 안에서만 찾기
  part_start_idx, part_end_idx = get_position_range(incorrect_part,
                                                    clause_start_idx)

  all_positions = extract_bboxes(clause_start_idx, clause_end_idx)
  part_positions = extract_bboxes(part_start_idx, part_end_idx)

  return all_positions, part_positions