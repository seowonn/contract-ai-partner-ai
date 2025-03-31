import os
from dotenv import load_dotenv

from app.common.constants import QDRANT_COLLECTION, TEST_COLLECTION

load_dotenv()


class AppConfig:
  APP_ENV = os.getenv("APP_ENV", "dev")
  QDRANT_HOST = "qdrant" if APP_ENV == "prod" else "localhost"
  QDRANT_PORT = 6333

  COLLECTION_NAME = QDRANT_COLLECTION if APP_ENV == "prod" else TEST_COLLECTION
