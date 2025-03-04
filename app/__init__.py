from flask import Flask
from app.blueprints.document_management import reference_document


def create_app():
  app = Flask(__name__)

  # 환경 변수 설정 로드

  # 블루 프린트 등록
  app.register_blueprint(reference_document.bp)

  # 예시 테스트 코드
  @app.route('/')
  def home():
    return "Hello, World!"

  return app