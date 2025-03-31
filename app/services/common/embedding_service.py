from typing import List

import httpx
import numpy as np
from openai import AsyncOpenAI

from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode


class EmbeddingService:
  def __init__(self, deployment_name):
    self.deployment_name = deployment_name

  async def embed_text(self, text: str) -> List[float]:
    async with httpx.AsyncClient() as httpx_client:
      async with AsyncOpenAI(http_client=httpx_client) as client:
        response = await client.embeddings.create(
            model=self.deployment_name,
            input=text,
            encoding_format="float"
        )

    if not response or not response.data or not response.data[0].embedding:
      raise CommonException(ErrorCode.EMBEDDING_FAILED)

    return np.array(response.data[0].embedding, dtype=np.float32).tolist()
