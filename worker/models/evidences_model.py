from datetime import date, datetime, time
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from worker.models.base import Base


class Evidence:
    complaint_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        ForeignKey("complaints.complaint_id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EvidenceMessage(Base, Evidence):
    __tablename__ = "evidence_messages"

    message_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)


class EvidenceVictim(Base, Evidence):
    __tablename__ = "evidence_victims"

    victim_id: Mapped[UUID] = mapped_column(
        "victim_id",
        PostgresUUID[UUID](as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class EvidenceVoice(Base, Evidence):
    __tablename__ = "evidence_voices"

    voice_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class EvidenceReportRecord(Base, Evidence):
    __tablename__ = "evidence_report_records"

    report_record_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


class EvidenceIncidentLogType(str, Enum):
    FILE = "FILE"
    FORM_DATA = "FORM_DATA"


class EvidenceIncidentLog(Base):
    __tablename__ = "evidence_incident_logs"

    incident_log_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    complaint_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        ForeignKey("complaints.complaint_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[EvidenceIncidentLogType] = mapped_column(
        SQLEnum(EvidenceIncidentLogType, native_enum=False, length=20), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EvidenceIncidentLogFile(Base):
    __tablename__ = "evidence_incident_log_files"

    incident_log_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        ForeignKey("evidence_incident_logs.incident_log_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)


class EvidenceIncidentLogFormData(Base):
    __tablename__ = "evidence_incident_log_form_data"

    incident_log_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        ForeignKey("evidence_incident_logs.incident_log_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)  # YYYY-MM-DD
    time: Mapped[time] = mapped_column(Time, nullable=False)  # HH:MM
    location: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    pdf_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="FORM_DATA PDF 최종 생성 시각. 재생성 필요 시 비교용",
    )
    pdf_s3_key: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="FORM_DATA PDF S3 키"
    )
