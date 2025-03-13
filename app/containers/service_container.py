from app.clients.openai_clients import embedding_client, \
  embedding_deployment_name, prompt_client, prompt_deployment_name
from app.services.common.embedding_service import EmbeddingService
from app.services.common.prompt_service import PromptService


embedding_service = EmbeddingService(embedding_client, embedding_deployment_name)
prompt_service = PromptService(prompt_client, prompt_deployment_name)