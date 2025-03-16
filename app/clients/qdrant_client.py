from qdrant_client import QdrantClient

from config.app_config import AppConfig

qdrant_db_client = QdrantClient(
    host=AppConfig.QDRANT_HOST,
    port=AppConfig.QDRANT_PORT
)