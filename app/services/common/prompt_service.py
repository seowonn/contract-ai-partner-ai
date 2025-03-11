from pydantic import json


class PromptService:
  def __init__(self, client, deployment_name):
    self.client = client
    self.deployment_name = deployment_name


  def make_correction_data(self, clause_content: str):
    response = self.client.chat.completions.create(
        model=self.deployment_name,
        messages=[
          {
            "role": "user",
            "content": f"""
              다음 문장은 특정 법률 조항에 따른 항 내용입니다. 이 조항을 기준으로 위반될 수 있는 문장을
              상상해서 하나 작성하고, 그 문장을 법률에 맞도록 수정한 교정 문장도 작성해주세요.
  
              반드시 아래와 같은 JSON 형태로만 응답하세요.
  
              문서 원문:
              \"\"\"
              {clause_content}
              \"\"\"
  
              [생성할 JSON 형식]
              {{
                "incorrect_text": "법률을 위반할 수 있는 예시 문장",
                "corrected_text": "위의 문장을 교정한 올바른 문장"
              }}
  
              조건:
              - 반드시 한국어로 작성.
              - 실제로 문제될 수 있는 자연스러운 문장으로 작성.
              - 위반 문장과 교정 문장은 서로 논리적으로 연결되어야 함.
              - 결과는 반드시 JSON만 반환. 설명, 추가 텍스트 없이.
            """
          }
        ],
        temperature=0.3,  # 정확성을 위해 낮게 (창의성을 낮춤)
        max_tokens=512,
        top_p=1
    )
    return json.loads(response.choices[0].message.content)