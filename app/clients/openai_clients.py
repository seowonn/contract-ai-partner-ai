import os

from dotenv import load_dotenv
from openai import AsyncOpenAI,OpenAI
import openai

load_dotenv() # 루트로 고정

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
sync_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

embedding_async_client = openai.AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
    api_version=os.getenv("AZURE_EMBEDDING_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_EMBEDDING_OPENAI_ENDPOINT")
)

embedding_sync_client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
    api_version=os.getenv("AZURE_EMBEDDING_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_EMBEDDING_OPENAI_ENDPOINT")
)
embedding_deployment_name = os.getenv("EMBEDDING_OPENAI_DEPLOYMENT_NAME")

prompt_async_client = openai.AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_PROMPT_API_KEY"),
    api_version=os.getenv("AZURE_PROMPT_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_PROMPT_OPENAI_ENDPOINT")
)
prompt_deployment_name = os.getenv("PROMPT_OPENAI_DEPLOYMENT_NAME")

vision_client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_VISION_API_KEY"),
    api_version=os.getenv("AZURE_VISION_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_VISION_OPENAI_ENDPOINT")
)
vision_deployment_name = os.getenv("AZURE_VISION_OPENAI_DEPLOYMENT_NAME")
