from typing import List

from app.common.exception.custom_exception import BaseCustomException
from app.common.exception.error_code import ErrorCode


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

    if not response or not response.data or not response.data[0].embedding:
      raise BaseCustomException(ErrorCode.EMBEDDING_FAILED)

    return response.data[0].embedding
