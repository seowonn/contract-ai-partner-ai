from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import config

# DB를 루트 환경에서 가져옴
db = SQLAlchemy()
migrate = Migrate()

# 전역 객체
# app = Flask(__name__)

# __name__ : 모듈 이름
def create_app():
    app = Flask(__name__)
    app.config.from_object(config)

    # db 객체 등록
    db.init_app(app)
    migrate.init_app(app, db)
    from . import models

    # 애너테이션으로 URL을 매핑하는 함수를 라우팅 함수라고 한다.
    # @app.route('/')
    # def hello_pybo():
    #     return 'Hello, Pybo!'

    # 블루프린트
    from .views import main_views, question_views, answer_views
    app.register_blueprint(main_views.bp)
    app.register_blueprint(question_views.bp)
    app.register_blueprint(answer_views.bp)

    return app
