import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.base.base_error import register_exception_handlers
from app.core.settings import settings
from app.dev.endpoints import router as dev_router

if settings.AWS_PROFILE:
    boto3.setup_default_session(profile_name=settings.AWS_PROFILE)

root_path = f"/{settings.env}"

app = FastAPI(title="AnsimOn Backend AI", root_path=root_path)

# 우선 로컬 개발용만 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 예외 핸들러 등록
register_exception_handlers(app)

print(settings.env)

if settings.env in ("dev", "local"):
    app.include_router(dev_router)


handler = Mangum(app)
