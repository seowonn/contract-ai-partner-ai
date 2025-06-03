import json
import logging
from typing import List, Any, Optional

from openai import AsyncAzureOpenAI

import re

from app.schemas.analysis_response import SearchResult


def clean_incorrect_part(text: str) -> str:
  particles = ['은', '는', '이', '가', '을', '를', '의', '에', '에서', '보다', '로', '과',
               '와']

  for particle in particles:
    # 마침표, 느낌표, 물음표 다음엔 조사 결합을 시도하지 않도록 예외 처리
    # 단어 + 공백 + 조사 이고, 그 앞에 구두점이 **없을 때만** 붙이기
    pattern = rf'(?<![\.!?])([가-힣])\s+{particle}(?=[\s\.,\)\"\'\”\’\]]|$)'
    replacement = rf'\1{particle}'
    text = re.sub(pattern, replacement, text)

  # 2칸 이상 공백은 1칸으로 줄이기
  text = re.sub(r'\s{2,}', ' ', text)

  return text


def clean_markdown_block(response_text: str) -> dict | None:
  response_text_cleaned = response_text

  if response_text_cleaned.startswith(
      "```json") and response_text_cleaned.endswith("```"):
    response_text_cleaned = response_text_cleaned[7:-3].strip()
  elif response_text_cleaned.startswith(
      "```") and response_text_cleaned.endswith("```"):
    response_text_cleaned = response_text_cleaned[3:-3].strip()

  try:
    parsed_response = json.loads(response_text_cleaned)
<<<<<<< HEAD
    if isinstance(parsed_response, list):
      parsed_response = parsed_response[0]

=======
>>>>>>> 6f2316a (Fork 이후 첫 커밋)
    if "incorrectPart" in parsed_response:
      parsed_response["incorrectPart"] = clean_incorrect_part(
          parsed_response["incorrectPart"])

    return parsed_response

  except json.JSONDecodeError as e:
    logging.error(
      f"[PromptService]: jsonDecodeError: {e} | raw response: {response_text_cleaned}")
    return None

class PromptService:
  def __init__(self, deployment_name):
    self.deployment_name = deployment_name


  async def make_additional_data(self, prompt_client: AsyncAzureOpenAI,
      clause_content: str) -> Any | None:
    response = await prompt_client.chat.completions.create(
        model=self.deployment_name,
        messages=[
          {
            "role": "system",
            "content": (
              "너는 계약 문장의 위배 가능성을 판단하고, 보다 공정한 문장으로 교정하는 법률 분석 전문가야.\n"
              "이때, 법적 책임 해석의 차이를 유발할 수 있는 용어도 함께 분석하고 설명해야 해.\n"
              "최종 출력은 반드시 JSON 형식으로 반환하며, key는 영어로, value는 자연스러운 한국어 문장으로 작성해."
            )
          },
          {
            "role": "user",
            "content": f"""
            입력 문장은 계약 체결자가 불리하게 해석할 여지가 있는지를 검토하는 대상이야.
<<<<<<< HEAD

=======
            
>>>>>>> 6f2316a (Fork 이후 첫 커밋)
            💡 작업 목표:
            1. 원문을 기반으로 **불공정하거나 불리하게 해석될 수 있는 문장 (incorrect_text)** 을 상상해서 작성
            2. 해당 문장을 보다 공정하게 고친 **교정 문장 (corrected_text)** 작성
            3. 해당 문장에서 **전문가와 비전문가 사이에 해석 차이를 유발할 수 있는 핵심 용어**를 식별하고, 그 **차이와 의미를 해설 (term_explanation)** 할 것
<<<<<<< HEAD

=======
            
>>>>>>> 6f2316a (Fork 이후 첫 커밋)
            📌 주의사항:
            - 원문 그대로 반환하지 말 것
            - 실제로 문서에 없더라도 **오해 가능성**이나 **맥락의 왜곡**에 근거해 위배 문장을 구성할 것
            - 맞춤법이나 단순한 문장 개선은 금지. **불공정성에만 집중할 것**
            - 반환 형식은 반드시 JSON이며, key는 다음과 같아야 함: `incorrect_text`, `corrected_text`, `term_explanation`
            - 응답은 하나의 JSON 객체로만 구성

            📎 출력 예시:
            {{
              "incorrect_text": "업무를 인계받지 못한 공무원은 아무런 책임이 없다.",
              "corrected_text": "업무를 인계받지 못한 공무원도, 특별한 사유가 없는 경우에는 책임을 질 수 있다.",
              "term_explanation": "‘책임이 없다’는 표현은 맥락에 따라 무조건 면책되는 것처럼 해석될 수 있어, 인계 지연의 원인을 고려하지 않는 불공정성이 있다."
            }}
<<<<<<< HEAD

            🎯 검토할 문장:
            \"\"\"{clause_content}\"\"\"

=======
      
            🎯 검토할 문장:
            \"\"\"{clause_content}\"\"\"
      
>>>>>>> 6f2316a (Fork 이후 첫 커밋)
            """
          }
        ],
        temperature=0.7,
        max_tokens=800,
        top_p=1
    )

    response_text = response.choices[0].message.content
    return clean_markdown_block(response_text)


  async def correct_contract(self, prompt_client: AsyncAzureOpenAI,
      clause_content: str, search_results: List[SearchResult]) -> Optional[
    dict[str, Any]]:

    clause_content = clause_content.replace("\n", " ")
    clause_content = clause_content.replace("+", "")
    clause_content = clause_content.replace("!!!", " ")

    input_data = {
      "clause_content": clause_content,
      "proof_text": [item.proof_text for item in search_results],
      "incorrect_text": [item.incorrect_text for item in search_results],
      "corrected_text": [item.corrected_text for item in search_results],
      "term_explanation": [item.term_explanation for item in search_results]
    }

    response = await prompt_client.chat.completions.create(
        model=self.deployment_name,
        messages=[
          {
            "role": "developer",
            "content":
              f"""
                너는 한국에서 계약서 및 법률 문서를 검토하는 최고의 변호사야.
                계약서에서 법률 위반 가능성이 있는 부분을 정확히 찾아내고,
                그 부분을 교정할 때 법적인 근거를 설명해야 해.
                특히 계약서 내 용어 사용이 오해를 일으킬 수 있는 경우, 
                관련 법률 용어의 정의와 해석 차이를 기준으로 다시 설명해 줘야 해.
              """
          },
          {
            "role": "user",
            "content":
              f"""
            입력 데이터를 참고해서 계약서 문장에서 부당한 문구가 있는지 찾아 수정해주세요.

            [특히 고려해야 할 사항]
            - 계약서 문장이 **법적 요건에 맞지 않거나**, **근로자에게 일방적으로 불리한 조건**을 담고 있다면 반드시 교정이 필요합니다.
            - 계약서 문장에서 전문가와 비전문가 사이에 해석 차이를 유발할 수 있는 용어가 등장하는 경우, 그 의미 차이와 오해의 가능성을 `proofText`에 설명해 주세요.
            - 해당 표현이 법률적 정의와 다르게 사용되어 문장이 잘못 해석될 수 있는 위험이 있다면, 그 위험성과 의미의 차이를 `proofText`에 해설해 주세요.
            - 문법적 오류보다는 **내용의 법적 타당성**에 집중해 주세요.
            - `proofText`에는 어떤 입력 변수명도 그대로 포함시키지 마세요.
            - 계약서 문장의 위배 확률이 높아 보인다면 `violation_score`를 높게 반환해 주세요.
<<<<<<< HEAD
            
            - 일반적으로 소정근로시간은 매일 09시부터 18시까지로 한다(휴게시간 제외 총 8시간, 1주간 40시간 이내로 함)
            - 초과되는 근무시간은 최대 주 12시간으로 하며, 연장근로 포함 총 근무시간은 주 52시간을 초과할 수 없습니다.
            
            - 2025년 시급은 10,030원 이상이여야만 합니다.
            - 근무시간이 주15시간 이상인 경우에만, 주휴수당이 별도로 지급되어야 하고 근무시간이 주 15시간 이하라면 급여에 포함이 아닌 지급되지 않아
            - 하자 담보 책임기간은 IT 업계에서 일반적으로 3개월~1년으로 합니다. 최소 1개월 이상이어야 합니다.
            - 일반적인 지체배상금요율은 0.005% ~ 0.3% 입니다. 반드시 1천분의 3 이하가 되어야합니다.

=======
            - proofText는 350자 이내로 작성해 주세요.
            
            - 2025년 시급은 10,030원 이상이여야만 합니다.
            - 근무시간이 주15시간 이상인 경우에만, 주휴수당이 별도로 지급되어야 하고 근무시간이 주 15시간 이하라면 급여에 포함이 아닌 지급되지 않아
>>>>>>> 6f2316a (Fork 이후 첫 커밋)
    
            [입력 데이터 설명]
            - clause_content: 계약서 문장
            - proof_text: 법률 문서의 문장 목록
            - incorrect_text: 법률 위반할 가능성이 있는 예시 문장 
            - corrected_text: 법률 위반 가능성이 있는 예시 문장을 올바르게 수정한 문장 목록
            - term_explanation: 핵심 용어의 전문적 의미와 비전문가가 오해할 수 있는 해석 차이를 설명한 해설

            [violation_score 판단 기준 및 생성 형식]
            - 반드시 "0.000"부터 "1.000" 사이의 **소수점 셋째 자리까지의 문자열(float 형식)**로 출력하세요.
            - `0.750`, `0.500`과 같이 끝자리가 `0`인 고정된 패턴은 피하고 다양성 있는 float 값을 사용해 주세요.
            - 소수점 셋째자리까지 0이 아닌 숫자를 넣어주세요
            - 무작위가 아닌, 문장의 위반 가능성을 기반으로 신중하게 결정해 주세요.

            [출력 형식]
            출력은 dict 형태이며, value 값은 반드시 문자열(string) 형태로 출력할 것:
            {{
              "correctedText": "계약서의 문장을 올바르게 교정한 문장",
              "proofText": "입력 데이터를 참조해 잘못된 포인트와 그 이유",
              "violation_score": "0.000 ~ 1.000 사이의 소수점 셋째 자리까지의 문자열"
                                  
              "incorrectPart": clause_content에서 문제가 되는 부분 길이는 최대 단어 5개까지 똑같이 반환해주세요.
                                     
                                     아래 규칙을 지켜주세요
                                     조사를 지우지 말고 완전한 문장을 반환하세요
                                     clause_content 문장과 일치하지 않고 부분 내용이여야 합니다.
                                     띄어쓰기, 온점, 반점, 괄호 등은 clause_content와 정확히 일치해야 합니다.
            }}
            
            [입력 데이터]
            {json.dumps(input_data, ensure_ascii=False, indent=2)}
          """
          }
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    response_text = response.choices[0].message.content
    return clean_markdown_block(response_text)