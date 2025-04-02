from qdrant_client import AsyncQdrantClient
from config.app_config import AppConfig

async_qdrant_client =  AsyncQdrantClient(
    host=AppConfig.QDRANT_HOST,
    port=AppConfig.QDRANT_PORT,
    timeout=60
)