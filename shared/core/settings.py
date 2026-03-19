import os

from dotenv import find_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# find_dotenv(): cwd에서 상위로 올라가며 .env 탐색 (프로젝트 루트)
# 배포 환경에서는 ENV != local → 플랫폼 환경변수만 사용
_ENV_FILE = find_dotenv() if os.getenv("ENV", "local") == "local" else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE or None,
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    env: str = Field(default="local", alias="ENV")
    WEB_APP_URL: str | None = None
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"], alias="CORS_ORIGINS"
    )

    DATABASE_URL: str | None = None

    AWS_REGION: str
    AWS_PROFILE: str | None = None
    COGNITO_CLIENT_ID: str | None = None
    COGNITO_USER_POOL_ID: str | None = None
    COGNITO_CLIENT_SECRET: str | None = None
    COGNITO_DOMAIN: str | None = None
    S3_BUCKET_NAME: str | None = None
    SQS_QUEUE_URL: str | None = None


settings = Settings()
