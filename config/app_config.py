import os
from dotenv import load_dotenv

from app.common.constants import Constants

load_dotenv()

class AppConfig:
    APP_ENV = os.getenv("APP_ENV", "dev")
    QDRANT_HOST = "qdrant" if APP_ENV == "prod" else "localhost"
    QDRANT_PORT = 6333

    COLLECTION_NAME = Constants.QDRANT_COLLECTION.value if APP_ENV == "prod" else Constants.TEST_COLLECTION.value