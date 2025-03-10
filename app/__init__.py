import os

from flask import Flask
from dotenv import load_dotenv
from app.common.exception.error_handler import register_error_handlers
from app.blueprints.standard import standard_blueprint

load_dotenv()

def create_app():
  app = Flask(__name__)

  # 환경 변수 설정 로드
  app.config.from_prefixed_env()
  app.config["API_KEY"] = os.getenv("API_KEY")

  # 예외 핸들러 등록
  register_error_handlers(app)

  # 블루 프린트 등록
  app.register_blueprint(standard_blueprint.standard)

  return app