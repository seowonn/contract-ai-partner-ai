from app.clients.openai_clients import embedding_deployment_name, prompt_deployment_name,openai_client
from app.services.common.embedding_service import EmbeddingService
from app.services.common.prompt_service import PromptService


embedding_service = EmbeddingService(embedding_deployment_name)
prompt_service = PromptService(prompt_deployment_name)
