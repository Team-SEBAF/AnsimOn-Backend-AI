from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.core.settings import settings

if not settings.DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# engine = DB 서버와의 연결 풀
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    # RDS/프록시가 유휴 TCP·SSL 연결을 끊기 전에 풀에서 재생성 (초). 긴 작업 없이도 오래 묵은 연결 방지.
    pool_recycle=280,
)

# Session = 실제 트랜잭션 단위 작업자
# sessionmaker = Session 클래스를 생성하는 팩토리 함수
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
