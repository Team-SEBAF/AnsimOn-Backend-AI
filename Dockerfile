# AI Worker (ECS Fargate용)
# Python 3.11 + Tesseract, Poppler 등 시스템 의존성

FROM python:3.11-slim-bookworm

# 시스템 패키지: Tesseract OCR, Poppler (pdf2image), ffmpeg (Whisper)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-kor \
    poppler-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Poetry 설치 (로컬과 동일한 2.x - dependency-groups 지원)
ENV POETRY_VERSION=2.2.1
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# 의존성만 먼저 설치 (캐시 활용)
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi -E worker \
    && rm -rf /root/.cache/pypoetry

# 프로젝트 코드 복사 (./scripts/clone_ai.sh로 ai/ 준비 후 빌드)
COPY ai/ ./ai/
COPY shared/ ./shared/
COPY worker/ ./worker/

ENV PYTHONPATH=/app:/app/ai/src
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "worker.main"]
