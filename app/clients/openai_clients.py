import os

from dotenv import load_dotenv
import openai

load_dotenv() # 루트로 고정

embedding_client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
    api_version="2023-05-15",
    azure_endpoint=os.getenv("AZURE_EMBEDDING_OPENAI_ENDPOINT")
)
embedding_deployment_name = os.getenv("AZURE_EMBEDDING_OPENAI_DEPLOYMENT_NAME")


prompt_client = openai.AzureOpenAI(
    api_key=os.getenv("AZURE_PROMPT_API_KEY"),
    api_version="2024-10-21",
    azure_endpoint=os.getenv("AZURE_PROMPT_OPENAI_ENDPOINT")
)
prompt_deployment_name = os.getenv("AZURE_PROMPT_OPENAI_DEPLOYMENT_NAME")
