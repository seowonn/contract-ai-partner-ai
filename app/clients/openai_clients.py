import logging
import os
from contextlib import asynccontextmanager, contextmanager

import httpx
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI, AzureOpenAI

from app.common.constants import EMBEDDING_MODEL, PROMPT_MODEL

load_dotenv() # 루트로 고정

# openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# sync_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@asynccontextmanager
async def get_dense_embedding_async_client():
  async with AsyncAzureOpenAI(
      api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
      api_version="2023-05-15",
      azure_endpoint=os.getenv("AZURE_EMBEDDING_OPENAI_ENDPOINT"),
  ) as client:
    yield client


@contextmanager
def get_embedding_sync_client():
  client = AzureOpenAI(
      api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
      api_version="2023-05-15",
      azure_endpoint=os.getenv("AZURE_EMBEDDING_OPENAI_ENDPOINT")
  )
  try:
    yield client
  finally:
    client.close()

embedding_deployment_name = EMBEDDING_MODEL


@asynccontextmanager
async def get_prompt_async_client():
  httpx_client = httpx.AsyncClient(
      timeout=httpx.Timeout(timeout=30.0, connect=30.0),
      http2=False
  )
  async with httpx_client:
    async with AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_PROMPT_API_KEY"),
        api_version="2025-01-01-preview",
        azure_endpoint=os.getenv("AZURE_PROMPT_OPENAI_ENDPOINT"),
        http_client=httpx_client
    ) as client:
      ad = os.getenv("AZURE_PROMPT_OPENAI_ENDPOINT")
      logging.info(f"endpoint: {ad}")
      yield client

prompt_deployment_name = PROMPT_MODEL
