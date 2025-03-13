# Flask용 Dockerfile
FROM python:3.9-slim

# 작업 디렉터리 생성
WORKDIR /app

# 프로젝트 파일 복사
COPY . .

# 필요한 패키지 설치
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn

# Flask 실행 (Beanstalk이 포트 5000으로 자동 매핑)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:create_app()"]