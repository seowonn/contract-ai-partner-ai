import json
import logging
import re
from typing import List, Any

import httpx
from openai import AsyncOpenAI

from app.clients.openai_clients import sync_openai_client


class PromptService:
  def __init__(self, deployment_name):
    self.deployment_name = deployment_name

  async def make_correction_data(self, clause_content: str) -> Any | None:
    async with httpx.AsyncClient() as httpx_client:
      async with AsyncOpenAI(http_client=httpx_client) as client:
        response = await client.chat.completions.create(
            model=self.deployment_name,
            messages=[
              {
                "role": "user",
                "content": f"""
                    너는 입력으로 들어온 문장을 보고 '계약 체결자에게 불리하게 작용할 수 있는 문장'을 생성하고, 이를 공정하게 수정하는 문장을 제시하는 전문가야.
    
                    아래 조건을 반드시 지켜.
                    - 계약자에게 불리한 문장을 찾지 못하더라도 원문 그대로 반환하지 말고 '불리할 여지가 있는 해석'을 적극적으로 추정할 것.
                    - 줄바꿈 없이 한 줄짜리 JSON만 출력할 것.
                    - 맞춤법 관련 내용은 제외.
                    - 반드시 아래와 같은 JSON 형식만 출력:
                      {{
                        "incorrect_text": "원문을 보고 위배 소지가 될 수 있는 문장을 생성한 문장",
                        "corrected_text": "공정하게 수정한 문장"
                      }}
    
                    원문:
                    \"\"\"
                    {clause_content}
                    \"\"\"
    
                    위배 판단 기준:
                    - 일방의 권리를 과도하게 제한하거나
                    - 해석 여지가 있어 불리한 결과가 나올 수 있으며
                    - 효력 발생 조건이 불공정한 경우 등
    
                    지금 문서를 분석해서 JSON으로 한 줄만 반환해.
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


  async def correct_contract(self, clause_content: str, proof_text: List[str],
      incorrect_text: List[str], corrected_text: List[str]):

    clause_content = clause_content.replace("\n", " ")
    clause_content = clause_content.replace("+", "")
    clause_content = clause_content.replace("!!!", "")


    # ✅ JSON 형식으로 변환할 데이터
    input_data = {
      "clause_content": clause_content,
      "proof_text": proof_text,
      "incorrect_text": incorrect_text,
      "corrected_text": corrected_text
    }

    async with httpx.AsyncClient() as httpx_client:
      async with AsyncOpenAI(http_client=httpx_client) as client:
        response = await client.chat.completions.create(
            model=self.deployment_name,
            messages=[
              {
                "role": "user",
                "content": f"""
                        clause_content, incorrect_text, proof_text 를 참고해서
                        입력받은 clause_content 에서 부당한 문구가 있는지 찾고 올바르게 수정해줘
                        위배된 확률 violation_score 을 계산해서 소수점 3자리로 반환해줘
                        틀린 확률이 높아보인다면 violation_score를 높게 반환해줘
                        교정한 이유는 proofText 에 적어주고 json 바깥에는 아무것도 반환하면 안돼
                        문법적인 내용은 배제하고 내용적인 측면에서 문장을 교정해줘
    
                        [입력 데이터 설명]
                        - clause_content: 수정해야하는 계약서의 문장
                        - proof_text: 기준이 되는 법률 문서의 문장 목록
                        - incorrect_text: 법률을 위반할 가능성이 있는 예시 문장 
                        - corrected_text: 법률 위반 가능성이 있는 예시 문장을 올바르게 수정한 문장 목록
    
                        [입력 데이터]
                        {json.dumps(input_data, ensure_ascii=False, indent=2)}
    
                        [출력 형식]
                        {{
                            "clause_content": 계약서 원문
                            "correctedText": "계약서의 문장을 올바르게 교정한 문장",
                            "proofText": 입력데이터를 참조해 잘못된 포인트와 이유"
                            "violation_score": "위배된 비율, 신뢰도, 무조건 소수점 셋째 자리까지 반환 0.888 과 같이"
                        }}
    
                        [조건]
                        - 위반 문장과 교정 문장은 서로 논리적으로 연결되어야 함
                    """
              }
            ],
            temperature=0.5,
        )

    response_text = response.choices[0].message.content
    response_text_cleaned = response_text.strip()

    if response_text_cleaned.startswith(
        "```json") and response_text_cleaned.endswith("```"):
      pure_json = response_text_cleaned[7:-3].strip()
    elif response_text_cleaned.startswith(
        "```") and response_text_cleaned.endswith("```"):
      pure_json = response_text_cleaned[3:-3].strip()
    else:
      pure_json = response_text_cleaned

    try:
      parsed_response = json.loads(pure_json)
    except json.JSONDecodeError:
      logging.error(
          f"[PromptService] ❌ OpenAI 응답이 JSON 형식이 아님:\n{response_text_cleaned}"
      )
      return None

    return parsed_response


  def summarize_document(self, documents: str) -> str:
    # OpenAI API 호출하여 문서 요약
    response = sync_openai_client.chat.completions.create(
        model=self.deployment_name,
        messages=[{
          "role": "user",
          # 과 엔터키 '\n', '\n\n' 모두 제거하고 출력해줘"
          "content": f"문서 전체 내용을 요약해줘."
                     f"출력할때 강조하는 '**'  제거하고 출력해줘"
                     f"\n\n 문서 : {documents}"
        }],
        temperature=0.5,
        top_p=1
    )

    # 요약된 내용만 추출하여 반환
    summary_content = response.choices[
      0].message.content if response.choices else ''

    return summary_content