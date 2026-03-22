from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from shared.core.settings import settings
from sse.tasks import router as sse_router

root_path = f"/{settings.env}"

app = FastAPI(title="AnsimOn Backend AI SSE", root_path=root_path)

# 우선 로컬 개발용만 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(sse_router)

handler = Mangum(app)
