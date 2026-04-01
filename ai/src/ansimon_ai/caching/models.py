from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Caching(Base):
    __tablename__ = "cachings"

    hash_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
