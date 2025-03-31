import os
from dotenv import load_dotenv


load_dotenv()


class AppConfig:
  APP_ENV = os.getenv("APP_ENV", "dev")
  QDRANT_HOST = "qdrant" if APP_ENV == "prod" else "localhost"
  QDRANT_PORT = 6333
