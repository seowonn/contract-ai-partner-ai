import os

from flask import Flask
from dotenv import load_dotenv
from app.blueprints.document_management import reference_document

load_dotenv()

def create_app():
  app = Flask(__name__)

  # 환경 변수 설정 로드
  app.config.from_prefixed_env()
  app.config["API_KEY"] = os.getenv("API_KEY")

  # 블루 프린트 등록
  app.register_blueprint(reference_document.document)

  return app