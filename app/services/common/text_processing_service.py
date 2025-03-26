import json
import logging
import os
import re
from typing import List, Any

from openai import AsyncOpenAI

from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode


class TextProcessingService:
  def __init__(self, client: AsyncOpenAI):
    self.client = client

  async def embed_text(self, text: str) -> List[float]:
    response = await self.client.embeddings.create(
        model=os.getenv("EMBEDDING_OPENAI_DEPLOYMENT_NAME"),
        input=text,
        encoding_format="float"
    )

    if not response or not response.data or not response.data[0].embedding:
      raise BaseCustomException(ErrorCode.EMBEDDING_FAILED)

    return response.data[0].embedding

  async def make_correction_data(self, clause_content: str) -> Any | None:
    response = await self.client.chat.completions.create(
        model=os.getenv("PROMPT_OPENAI_DEPLOYMENT_NAME"),
        messages=[
          {
            "role": "user",
            "content": f"""
              다음 지시문에 맞게 반환 해줘
              반드시 JSON 코드 블록 (```json ...) 을 사용하지 말고, 그냥 JSON 객체만 반환해
              JSON 문자열 내 줄바꿈(\n)이 포함되지 않도록 한 줄로 작성해줘

              문서 원문:
              \"\"\"
              {clause_content}
              \"\"\"

              [생성할 JSON 형식]
              {{
                "incorrect_text": "문서 원문을 기준으로 법률을 위반할 수 있는 예시 문장",
                "corrected_text": "위의 문장을 교정한 문장"
              }}

              조건:
              - 위반 문장과 교정 문장은 서로 논리적으로 연결되어야 함.
              - 결과는 반드시 JSON만 반환. 설명, 추가 텍스트 없이.
            """
          }
        ],
        temperature=0.5,
        max_tokens=512,
        top_p=1
    )

    response_text = response.choices[0].message.content
    response_text_cleaned = re.sub(r'(?<!\\)\n', ' ', response_text).strip()
    try:
      parsed_response = json.loads(response_text_cleaned)
    except json.JSONDecodeError:
      logging.error(f"[PromptService]: jsonDecodeError response_text {response_text_cleaned}")
      return None

    return parsed_response