# AI Worker (ECS Fargate용)
# Python 3.11 + Tesseract, Poppler 등 시스템 의존성

FROM python:3.11-slim-bookworm

# 시스템 패키지: Tesseract OCR, Poppler (pdf2image), ffmpeg (Whisper), git (ai 클론용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-kor \
    poppler-utils \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Poetry 설치
ENV POETRY_VERSION=1.8.3
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# 의존성만 먼저 설치 (캐시 활용)
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# AI 모듈 클론 (별도 레포)
RUN git clone --depth 1 https://github.com/Team-SEBAF/AnsimOn-AI.git ai_temp \
    && mkdir -p ai \
    && mv ai_temp/src ai/ \
    && rm -rf ai_temp

# 프로젝트 코드 복사
COPY shared/ ./shared/
COPY worker/ ./worker/

ENV PYTHONPATH=/app:/app/ai/src
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "worker.main"]
