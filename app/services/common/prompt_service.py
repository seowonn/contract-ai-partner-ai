

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