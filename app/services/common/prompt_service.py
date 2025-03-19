import json
import logging
from typing import List


class PromptService:
  def __init__(self, client, deployment_name):
    self.client = client
    self.deployment_name = deployment_name

  def make_correction_data(self, clause_content: str) -> str:
    response = self.client.chat.completions.create(
        model=self.deployment_name,
        messages=[
          {
            "role": "user",
            "content": f"""
              다음 지시문에 맞게 반환 해줘

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
    return response.choices[0].message.content

  def correct_contract(self, clause_content: str, proof_texts: List[str],
      incorrect_texts: List[str], corrected_texts: List[str]):
    # ✅ JSON 형식으로 변환할 데이터
    input_data = {
      "clause_content": clause_content,
      "proof_texts": proof_texts,
      "incorrect_texts": incorrect_texts,
      "corrected_texts": corrected_texts
    }

    response = self.client.chat.completions.create(
        model=self.deployment_name,
        messages=[
          {
            "role": "user",
            "content": f"""
                    예시 위배 문장과 예시 위배 교정 문장을 참고해서 
                    입력받은 계약서 문장을 기준 문서(법률 조항)과 비교하여 교정해줘.
                    그리고 참고한 자료를 기반으로 위배된 비율, 신뢰도(accuracy) 0.5 넘은 것만 알려줘
                    반드시 JSON 코드 블록 (```json ...) 을 사용하지 말고, 그냥 JSON 객체만 반환해.
                    특히 'proof_texts', 'incorrect_texts', 'corrected_texts'는 리스트가 아닌 단일 문자열로 반환해야 해.

                    [입력 데이터 설명]
                    - **clause_content**: 사용자가 입력한 계약서의 문장 (수정해야 하는 문장)
                    - **proof_texts**: 기준이 되는 법률 문서의 문장 목록 (계약서와 비교할 법률 조항들)
                    - **incorrect_texts**: 법률을 위반할 가능성이 있는 문장 예시 목록
                    - **corrected_texts**: 법률 위반 가능성이 있는 예시 문장을 올바르게 수정한 문장 목록

                    [입력 데이터]
                    {json.dumps(input_data, ensure_ascii=False, indent=2)}

                    [출력 형식]
                    {{
                        "clause_content": "{clause_content}",
                        "corrected_text": "계약서의 문장을 올바르게 교정한 문장",
                        "proof_text": "proof_texts, incorrect_texts, corrected_texts 를 참조해 잘못된 포인트와 이유 문장",
                        "accuracy": "위배된 비율, 신뢰도"
                    }}

                    [조건]
                    - 위반 문장과 교정 문장은 서로 논리적으로 연결되어야 함,
                    - 결과는 반드시 JSON 형식으로 반환해
                """
          }
        ],
        temperature=0.5,
        top_p=1
    )

    response_text = response.choices[0].message.content

    # ✅ JSON 변환 시도
    try:
      parsed_response = json.loads(response_text)
    except json.JSONDecodeError:
      logging.error(f"❌ OpenAI 응답이 JSON 형식이 아님: {response_text}")
      return None  # JSON 변환 실패 시 None 반환

    return parsed_response
