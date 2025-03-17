class VisionService:
  def __init__(self, client, deployment_name):
    self.client = client
    self.deployment_name = deployment_name

  def extract_text_by_vision(self, image_url: str) -> str:
    response = self.client.chat.completions.create(
        model=self.deployment_name,
        messages=[
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
    return extracted_text