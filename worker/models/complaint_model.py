from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from worker.models.base import Base


class ComplaintStep(str, Enum):
    """고소장 작성 단계"""

    EVIDENCE = "EVIDENCE"
    TIMELINE = "TIMELINE"
    DOCUMENT = "DOCUMENT"
    COMPLETE = "COMPLETE"


class Complaint(Base):
    __tablename__ = "complaints"

    complaint_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_sub: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.user_sub", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, default="고소장 제목")
    step: Mapped[ComplaintStep] = mapped_column(
        SQLEnum(ComplaintStep, native_enum=False, length=20),
        nullable=False,
        default=ComplaintStep.EVIDENCE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
