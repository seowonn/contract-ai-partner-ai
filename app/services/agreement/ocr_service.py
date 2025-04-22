import re
import uuid
from typing import List, Tuple
import numpy as np
import cv2
import json
import time
import os
from dotenv import load_dotenv


from app.common.constants import ARTICLE_OCR_HEADER_PATTERN, \
  CLAUSE_HEADER_PATTERN, ARTICLE_CLAUSE_SEPARATOR
from app.schemas.analysis_response import RagResult, ClauseData
from app.schemas.chunk_schema import Document, DocumentChunk, DocumentMetadata
from app.services.common.chunking_service import split_by_clause_header_pattern, \
  MIN_CLAUSE_BODY_LENGTH, get_clause_pattern, split_text_by_pattern, \
  chunk_preamble_content, check_if_preamble_exists_except_first_page, \
  parse_article_header
import requests


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

  # URL에서 이미지를 다운로드

  image_response = requests.get(image_url)
  image_data = image_response.content

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

  # OCR 요청 보내기
  response = requests.request("POST", NAVER_CLOVA_API_URL, headers=headers, data=payload,
                              files=files)
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