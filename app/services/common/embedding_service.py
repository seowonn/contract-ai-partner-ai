from typing import List


class EmbeddingService:
  def __init__(self, client, deployment_name):
    self.client = client
    self.deployment_name = deployment_name

  def embed_text(self, text: str) -> List[float]:
    response = self.client.embeddings.create(
        model=self.deployment_name,
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding
