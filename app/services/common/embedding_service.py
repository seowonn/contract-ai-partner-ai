from typing import List

import numpy as np
from openai import AsyncAzureOpenAI, AzureOpenAI

from app.common.exception.custom_exception import CommonException
from app.common.exception.error_code import ErrorCode

MAX_BATCH_SIZE = 32


class EmbeddingService:
  def __init__(self, deployment_name):
    self.deployment_name = deployment_name


  async def batch_embed_texts(self, embedding_client: AsyncAzureOpenAI,
      inputs: List[str]) -> List[List[float]]:

    all_embeddings = []
    for i in range(0, len(inputs), MAX_BATCH_SIZE):
      batch = inputs[i:i + MAX_BATCH_SIZE]
      try:
        embeddings = await self.embed_texts(embedding_client, batch)
        all_embeddings.extend(embeddings)
      except Exception:
        raise CommonException(ErrorCode.EMBEDDING_FAILED)
    return all_embeddings


  async def embed_texts(self, embedding_client: AsyncAzureOpenAI,
      sentences: List[str]) -> List[List[float]]:
    response = await embedding_client.embeddings.create(
        input=sentences,
        model=self.deployment_name,
        encoding_format="float"
    )

    if not response or not response.data or not response.data[0].embedding:
      raise CommonException(ErrorCode.EMBEDDING_FAILED)

    return [np.array(d.embedding, dtype=np.float32).tolist() for d in
            response.data]


  def batch_sync_embed_texts(self, embedding_client: AzureOpenAI,
      inputs: List[str]) -> List[List[float]]:
    all_embeddings = []
    for i in range(0, len(inputs), MAX_BATCH_SIZE):
      batch = inputs[i:i + MAX_BATCH_SIZE]
      try:
        embeddings = self.get_embeddings(embedding_client, batch)
        all_embeddings.extend(embeddings)
      except Exception:
        raise CommonException(ErrorCode.EMBEDDING_FAILED)
    return all_embeddings


  def get_embeddings(self, embedding_client: AzureOpenAI,
      sentences: List[str]) -> List[List[float]]:
    response = embedding_client.embeddings.create(
        input=sentences,
        model=self.deployment_name,
        encoding_format="float"
    )

    if not response or not response.data or not response.data[0].embedding:
      raise CommonException(ErrorCode.EMBEDDING_FAILED)

    return [np.array(d.embedding, dtype=np.float32).tolist() for d in
            response.data]
