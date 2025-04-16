import re
import uuid
from typing import List, Tuple
import numpy as np
import cv2
import json
import time

from app.common.constants import ARTICLE_OCR_HEADER_PATTERN, \
  CLAUSE_HEADER_PATTERN, ARTICLE_CLAUSE_SEPARATOR
from app.schemas.analysis_response import RagResult, ClauseData
from app.schemas.chunk_schema import Document, DocumentChunk, DocumentMetadata
from app.services.common.chunking_service import split_by_clause_header_pattern, \
  MIN_CLAUSE_BODY_LENGTH, get_clause_pattern, split_text_by_pattern
import requests



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

def parse_ocr_to_documents(full_text :str) -> List[Document]:
  documents: List[Document] = []

  meta = DocumentMetadata(page = 1)
  documents.append(Document(
      page_content=full_text,
      metadata=meta
  ))

  return documents


def chunk_by_article_and_clause_without_page_ocr(
    documents: List[Document]) -> List[DocumentChunk]:
  chunks: List[DocumentChunk] = []

  for doc in documents:
    page_text = doc.page_content
    order_index = 1
    page = 1


    matches = re.findall(ARTICLE_OCR_HEADER_PATTERN, page_text, flags=re.DOTALL)
    for header, body in matches:
      first_clause_match = re.search(CLAUSE_HEADER_PATTERN, body)
      if first_clause_match and body.startswith(
          first_clause_match.group(1)):

        clause_chunks = (
          split_by_clause_header_pattern(
              first_clause_match.group(1), "\n" + body))

        for j in range(1, len(clause_chunks), 2):
          clause_number = clause_chunks[j].strip()
          if clause_number.endswith("."):
            clause_number = clause_number[:-1]

          clause_content = clause_chunks[j + 1].strip() if j + 1 < len(
              clause_chunks) else ""

          if len(clause_content) >= MIN_CLAUSE_BODY_LENGTH:
            chunks.append(DocumentChunk(
                clause_content=f"{header}{ARTICLE_CLAUSE_SEPARATOR}\n{clause_content}",
                page=page,
                order_index=order_index,
                clause_number=f"제{header}조 {clause_number}항"
            ))
            order_index += 1
      else:
        if len(body) >= MIN_CLAUSE_BODY_LENGTH:
          chunks.append(DocumentChunk(
              clause_content=f"{header}{ARTICLE_CLAUSE_SEPARATOR}\n{body}",
              page=page,
              order_index=order_index,
              clause_number=f"제{header}조 1항"
          ))
          order_index += 1

  return chunks



def combine_chunks_by_clause_number_ocr(
    document_chunks: List[DocumentChunk]) -> List[RagResult]:
  combined_chunks: List[RagResult] = []

  for doc in document_chunks:
    combined_chunks.append(
        RagResult(
            incorrect_text=doc.clause_content,
            clause_data=[ClauseData(
                order_index=doc.order_index,
                page=doc.page)]
        )
    )

  return combined_chunks



def extract_ocr(image_url: str) -> Tuple[str, List[dict]]:

  api_url = 'https://j1gc26xlo7.apigw.ntruss.com/custom/v1/40588/33fe635b5703b4f6d707423be0d20bb9db938ef92692a5bf2aa1bee17d1b8e34/general'
  secret_key = 'eEh6bmFEQXppU3dSS3JkTENtbk1QZFdJcmpSRGNkd2c='

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
    'X-OCR-SECRET': secret_key
  }

  # OCR 요청 보내기
  response = requests.request("POST", api_url, headers=headers, data=payload,
                              files=files)
  ocr_results = json.loads(response.text)


  all_texts_with_bounding_boxes = []  # 텍스트와 바운딩 박스를 묶어서 저장할 리스트

  # OCR 결과에서 텍스트와 바운딩 박스를 묶어서 리스트로 저장
  for image_result in ocr_results['images']:
    for field in image_result['fields']:
      text = field['inferText']
      bounding_box = field['boundingPoly']['vertices']

      # 상대적인 좌표로 변환
      relative_bounding_box = []
      for vertex in bounding_box:
        x_rel = vertex['x'] / width  # x 좌표를 이미지 너비로 나누어 비율 계산
        y_rel = vertex['y'] / height  # y 좌표를 이미지 높이로 나누어 비율 계산
        relative_bounding_box.append({'x': x_rel, 'y': y_rel})

        # 텍스트와 상대적인 바운딩 박스를 하나의 딕셔너리로 묶어서 리스트에 추가
      all_texts_with_bounding_boxes.append({
        'text': text,
        'bounding_box': relative_bounding_box
      })

  # 텍스트 결합하기 (각 텍스트를 공백 기준으로 결합)
  full_text = " ".join([item['text'] for item in all_texts_with_bounding_boxes])

  return full_text, all_texts_with_bounding_boxes