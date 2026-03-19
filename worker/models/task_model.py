from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from worker.models.base import Base


class TaskType(str, Enum):
    """AI 태스크 타입"""

    TIMELINE = "TIMELINE"
    DOCUMENT = "DOCUMENT"


class TaskStatus(str, Enum):
    """AI 태스크 상태"""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    type: Mapped[TaskType] = mapped_column(
        SQLEnum(TaskType, native_enum=False, length=20),
        nullable=False,
    )
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus, native_enum=False, length=20),
        nullable=False,
        default=TaskStatus.PENDING,
    )
    complaint_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        ForeignKey("complaints.complaint_id", ondelete="CASCADE"),
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
