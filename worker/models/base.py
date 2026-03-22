"""모든 모델이 공유하는 Base. ForeignKey 참조를 위해 단일 Base 사용."""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
