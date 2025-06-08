from typing import Optional

from qdrant_client import AsyncQdrantClient
from config.app_config import AppConfig

def get_qdrant_client() -> AsyncQdrantClient:
  return AsyncQdrantClient(
      host=AppConfig.QDRANT_HOST,
      port=AppConfig.QDRANT_PORT,
      timeout=60
  )


_qd_client: Optional[AsyncQdrantClient] = None

def get_singleton_qdrant_client() -> AsyncQdrantClient:
    global _qd_client
    if _qd_client is None:
        _qd_client = AsyncQdrantClient(
            host=AppConfig.QDRANT_HOST,
            port=AppConfig.QDRANT_PORT,
            timeout=60
        )
    return _qd_client