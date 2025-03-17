import logging
import os

from dotenv import load_dotenv
from flask import Flask
from app.clients.qdrant_client import qdrant_db_client
from app.clients.openai_clients import embedding_client, prompt_client
from app.common.exception.error_handler import register_error_handlers
from app.blueprints.standard import standard_blueprint
from app.blueprints.agreement import agreement_blueprint
from flask import jsonify

load_dotenv()

def create_app():
  app = Flask(__name__)

  # 환경 구분
  app_env = os.getenv("APP_ENV", "dev")
  app.config["APP_ENV"] = app_env

  # 로깅 설정
  werkzeug_logger = logging.getLogger('werkzeug')
  werkzeug_logger.disabled = True
  logging.basicConfig(level=logging.DEBUG)

  @app.route('/healthz', methods=['GET'])
  def health_check():
    return jsonify({"status": "healthy"}), 200

  # 예외 핸들러 등록
  register_error_handlers(app)

  # 블루 프린트 등록
  app.register_blueprint(standard_blueprint.standards)
  app.register_blueprint(agreement_blueprint.agreements)

  return app