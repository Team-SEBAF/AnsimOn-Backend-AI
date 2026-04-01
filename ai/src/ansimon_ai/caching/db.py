import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# engine = DB 서버와의 연결 풀
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# Session = 실제 트랜잭션 단위 작업자
# sessionmaker = Session 클래스를 생성하는 팩토리 함수
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
