from typing import List

import httpx
import numpy as np
from openai import AsyncOpenAI

from app.clients.openai_clients import embedding_async_client, \
  embedding_sync_client
from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode

MAX_BATCH_SIZE = 32


class EmbeddingService:
  def __init__(self, deployment_name):
    self.deployment_name = deployment_name

  async def embed_text(self, text: str) -> List[float]:
    # async with httpx.AsyncClient() as httpx_client:
    #   async with AsyncOpenAI(http_client=httpx_client) as client:
    response = await embedding_async_client.embeddings.create(
        model=self.deployment_name,
        input=text,
        encoding_format="float"
    )

    if not response or not response.data or not response.data[0].embedding:
      raise CommonException(ErrorCode.EMBEDDING_FAILED)

    return np.array(response.data[0].embedding, dtype=np.float32).tolist()


  def batch_sync_embed_texts(self, inputs: List[str]) -> List[List[float]]:
    all_embeddings = []
    for i in range(0, len(inputs), MAX_BATCH_SIZE):
      batch = inputs[i:i + MAX_BATCH_SIZE]
      try:
        embeddings = self.get_embeddings(batch)
        all_embeddings.extend(embeddings)
      except Exception:
        raise CommonException(ErrorCode.EMBEDDING_FAILED)
    return all_embeddings


  def get_embeddings(self, sentences: List[str]) -> List[List[float]]:
    response = embedding_sync_client.embeddings.create(
        input=sentences,
        model=self.deployment_name,
        encoding_format="float"
    )
    return [np.array(d.embedding, dtype=np.float32).tolist() for d in response.data]


  async def embed_texts(self, sentences: List[str]) -> List[List[float]]:
    response = await embedding_async_client.embeddings.create(
        input=sentences,
        model=self.deployment_name,
        encoding_format="float"
    )
    return [np.array(d.embedding, dtype=np.float32).tolist() for d in response.data]