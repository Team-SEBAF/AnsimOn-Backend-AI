from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.types import DateTime
from sqlalchemy.sql import func
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Caching(Base):
    __tablename__ = "cachings"

    hash_key: Mapped[str] = mapped_column(String(512), primary_key=True)
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    complaint_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        ForeignKey("complaints.complaint_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
