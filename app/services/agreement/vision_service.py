import requests
import uuid
import time
import json
import cv2
import numpy as np

class VisionService:
  def __init__(self, client, deployment_name):
    self.client = client
    self.deployment_name = deployment_name

  def extract_text_by_vision(self, image_url: str) -> str:
    response = self.client.chat.completions.create(
        model=self.deployment_name,
        messages=[
          {"role": "system", "content": "이미지에서 모든 텍스트를 정확하게 추출해줘. 요약하지 말고, 있는 그대로 반환해줘. 불필요한 설명 없이 텍스트만 출력해."},
          {"role": "user", "content": [
            {
              "type": "image_url",
              "image_url": {
                "url": image_url
              }
            }
          ]}
        ],
        max_tokens=2000
    )

    extracted_text = response.choices[0].message.content

    # 영어 문구 제거 (추출된 텍스트만 반환)
    extracted_text = extracted_text.strip("```").strip()  # 앞뒤 코드 블록 제거
    return extracted_text


def extract_ocr(image_url: str):

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
  # 결과 출력
  # print(full_text)

  return full_text, all_texts_with_bounding_boxes