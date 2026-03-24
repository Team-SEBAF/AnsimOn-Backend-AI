from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.core.settings import settings
from sse.tasks import router as sse_router

# API Gateway 스테이지 등 공개 URL 접두와 맞추려면 ENV를 스테이지 이름과 동일하게.
app = FastAPI(title="AnsimOn Backend AI SSE", root_path=f"/{settings.env}")

# 우선 로컬 개발용만 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(sse_router)
