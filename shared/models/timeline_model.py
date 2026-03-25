from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base


class Timeline(Base):
    __tablename__ = "timelines"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    complaint_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        ForeignKey("complaints.complaint_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    timeline_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    need_timeline_regeneration: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="타임라인 JSON 재생성 필요 여부",
    )
    need_evidence_collection_regeneration: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="대조 증거 모음 재생성 필요 여부",
    )
    need_timeline_pdf_regeneration: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="타임라인 PDF 재생성 필요 여부",
    )


class TimelineEvidence(Base):
    """타임라인 증거. timeline JSON의 timeline_evidence_id와 연결.
    is_original_evidence=True: referenced_evidence_id → evidence_* 테이블
    is_original_evidence=False: referenced_manual_evidence_id → timeline_referenced_manual_evidences.id (FK)
    """

    __tablename__ = "timeline_evidences"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    timeline_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        ForeignKey("timelines.id", ondelete="CASCADE"),
        nullable=False,
    )
    timeline_evidence_id: Mapped[UUID] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        nullable=False,
        comment="timeline JSON 내 증거 그룹 id",
    )
    index: Mapped[int] = mapped_column(nullable=False, comment="원본 순서 1, 2, 3, ...")
    referenced_evidence_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        nullable=True,
        comment="evidence_* 테이블 id (is_original_evidence=True일 때)",
    )
    referenced_manual_evidence_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID[UUID](as_uuid=True),
        ForeignKey("timeline_referenced_manual_evidences.id", ondelete="CASCADE"),
        nullable=True,
        comment="timeline_referenced_manual_evidences.id (is_original_evidence=False일 때)",
    )
    is_original_evidence: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        comment="True: AI 분석 증거(evidence_*), False: 직접 추가(timeline_referenced_manual_evidences)",
    )
    evidence_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="MESSAGE, VICTIM, VOICE, REPORT_RECORD, INCIDENT_LOG (is_original_evidence=True일 때만)",
    )
    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="IMAGE, AUDIO, VIDEO, DOCUMENT, ETC (항상 존재)",
    )

    def get_evidence_id(self) -> UUID | None:
        """조회용 evidence id. is_original_evidence에 따라 referenced_evidence_id 또는 referenced_manual_evidence_id 반환."""
        return (
            self.referenced_evidence_id
            if self.is_original_evidence
            else self.referenced_manual_evidence_id
        )
