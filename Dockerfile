# Render 무료 인스턴스와 비슷한 조건으로 로컬에서 실행하기 위한 이미지
#   docker build -t waste-api .
#   docker run --rm -p 8000:8000 --memory=512m --cpus=0.1 waste-api
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY model_data ./model_data

EXPOSE 8000
# Render는 PORT 환경변수로 포트를 지정한다.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
