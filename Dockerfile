# Flask용 Dockerfile
FROM python:3.10-slim

# 작업 디렉터리 생성
WORKDIR /app

# 프로젝트 파일 복사
COPY requirements.txt .

# 필요한 패키지 설치
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn && \
    python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
RUN apt-get update && apt-get install -y \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0


COPY . .

# Flask 실행
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "3600", "run:create_app()"]
