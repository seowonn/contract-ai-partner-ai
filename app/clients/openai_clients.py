import os

from dotenv import load_dotenv
from openai import AsyncOpenAI,OpenAI
import openai

load_dotenv() # 루트로 고정

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
sync_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

embedding_async_client = openai.AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
    api_version="2023-05-15",
    azure_endpoint=os.getenv("AZURE_EMBEDDING_OPENAI_ENDPOINT")
)

embedding_sync_client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
    api_version="2023-05-15",
    azure_endpoint=os.getenv("AZURE_EMBEDDING_OPENAI_ENDPOINT")
)
embedding_deployment_name = "text-embedding-3-small"

prompt_async_client = openai.AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_PROMPT_API_KEY"),
    api_version="2025-01-01-preview",
    azure_endpoint=os.getenv("AZURE_PROMPT_OPENAI_ENDPOINT")
)
prompt_deployment_name = "gpt-4o-mini"