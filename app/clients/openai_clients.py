import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
import openai

load_dotenv() # 루트로 고정

embedding_client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
    api_version=os.getenv("AZURE_EMBEDDING_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_EMBEDDING_OPENAI_ENDPOINT")
)
embedding_deployment_name = os.getenv("AZURE_EMBEDDING_OPENAI_DEPLOYMENT_NAME")


prompt_client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_PROMPT_API_KEY"),
    api_version=os.getenv("AZURE_PROMPT_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_PROMPT_OPENAI_ENDPOINT")
)
prompt_deployment_name = os.getenv("AZURE_PROMPT_OPENAI_DEPLOYMENT_NAME")


vision_client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_VISION_API_KEY"),
    api_version=os.getenv("AZURE_VISION_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_VISION_OPENAI_ENDPOINT")
)
vision_deployment_name = os.getenv("AZURE_VISION_OPENAI_DEPLOYMENT_NAME")

openai.api_key = os.getenv("OPENAI_API_KEY")
openai_client = openai.Client()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))