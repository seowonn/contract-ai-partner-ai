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