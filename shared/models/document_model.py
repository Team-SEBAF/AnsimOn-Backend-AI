from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from shared.models.base import Base


class Document(Base):
    __tablename__ = "documents"

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
    complaint_form_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    statement_form_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    need_complaint_pdf_regeneration: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="고소장 PDF 재생성 필요 여부",
    )
    need_statement_pdf_regeneration: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="진술서 PDF 재생성 필요 여부",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# 폼 데이터 ----------------------------------------------------------------------------------


class ComplaintFormSection1Contacts(BaseModel):
    """1. 고소인 — 연락처."""

    mobile: str | None = Field(default=None, description="1. 고소인 — 연락처(휴대폰)")
    home: str | None = Field(default=None, description="1. 고소인 — 연락처(자택)")
    office: str | None = Field(default=None, description="1. 고소인 — 연락처(사무실)")


class ComplaintFormSection1Representative(BaseModel):
    """1. 고소인 — 대리인에 의한 고소."""

    is_legal_representative: bool = Field(
        default=False,
        description="1. 고소인 — 대리인: 법정대리인(체크)",
    )
    is_lawyer: bool = Field(
        default=False,
        description="1. 고소인 — 대리인: 변호사(체크)",
    )
    name: str | None = Field(default=None, description="1. 고소인 — 대리인 성명")
    contact: str | None = Field(default=None, description="1. 고소인 — 대리인 연락처")


class ComplaintFormSection1Complainant(BaseModel):
    """1. 고소인."""

    name_or_company: str | None = Field(
        default=None,
        description="1. 고소인 — 성명 / 상호",
    )
    resident_or_corp_registration_number: str | None = Field(
        default=None,
        description="1. 고소인 — 주민등록번호 / 법인등록번호",
    )
    address: str | None = Field(default=None, description="1. 고소인 — 주소")
    occupation: str | None = Field(default=None, description="1. 고소인 — 직업")
    office_address: str | None = Field(default=None, description="1. 고소인 — 사무실 주소")
    contact: ComplaintFormSection1Contacts = Field(
        default_factory=ComplaintFormSection1Contacts,
        description="1. 고소인 — 연락처(휴대폰·자택·사무실)",
    )
    email: str | None = Field(default=None, description="1. 고소인 — 이메일")
    representative: ComplaintFormSection1Representative = Field(
        default_factory=ComplaintFormSection1Representative,
        description="1. 고소인 — 대리인에 의한 고소",
    )


class ComplaintFormSection2Contacts(BaseModel):
    """2. 피고소인 — 연락처."""

    mobile: str | None = Field(default=None, description="2. 피고소인 — 연락처(휴대폰)")
    home: str | None = Field(default=None, description="2. 피고소인 — 연락처(자택)")
    office: str | None = Field(default=None, description="2. 피고소인 — 연락처(사무실)")


class ComplaintFormSection2Accused(BaseModel):
    """2. 피고소인."""

    name: str | None = Field(default=None, description="2. 피고소인 — 성명")
    resident_registration_number: str | None = Field(
        default=None,
        description="2. 피고소인 — 주민등록번호",
    )
    address: str | None = Field(default=None, description="2. 피고소인 — 주소")
    occupation: str | None = Field(default=None, description="2. 피고소인 — 직업")
    office_address: str | None = Field(default=None, description="2. 피고소인 — 사무실 주소")
    contact: ComplaintFormSection2Contacts = Field(
        default_factory=ComplaintFormSection2Contacts,
        description="2. 피고소인 — 연락처(휴대폰·자택·사무실)",
    )
    email: str | None = Field(default=None, description="2. 피고소인 — 이메일")
    other_details: str | None = Field(
        default=None,
        description="2. 피고소인 — 기타사항(인적 사항 특정 곤란 시 등)",
    )


class ComplaintFormSection3ComplaintPurpose(BaseModel):
    """3. 고소 취지."""

    content: str | None = Field(
        default=None,
        description="3. 고소 취지 — 본문(구하는 취지)",
    )


class ComplaintFormSection4CrimeFacts(BaseModel):
    """4. 범죄 사실."""

    content: str | None = Field(
        default=None,
        description="4. 범죄사실 — 본문(자유 서술)",
    )


class ComplaintFormSection5ComplaintReason(BaseModel):
    """5. 고소 이유."""

    content: str | None = Field(
        default=None,
        description="5. 고소 이유 — 본문",
    )


class ComplaintFormSection6Evidence(BaseModel):
    """6. 증거 자료."""

    has_evidence_beyond_statement: bool | None = Field(
        default=None,
        description="6. 증거 — 진술 외 제출 증거 있음/없음",
    )
    evidence_list_text: list[str] = Field(
        default_factory=list,
        description="6. 증거 — 제출물 목록(인적·물적, 항목별 한 줄)",
    )


class ComplaintFormSection7RelatedCases(BaseModel):
    """7. 관련 사건의 수사·재판 여부."""

    is_duplicate_complaint: bool | None = Field(
        default=None,
        description="7. 관련사건 — 중복 고소 여부(예·아니오)",
    )
    has_related_criminal_investigation: bool | None = Field(
        default=None,
        description="7. 관련사건 — 관련 형사 수사 여부",
    )
    has_related_civil_lawsuit: bool | None = Field(
        default=None,
        description="7. 관련사건 — 관련 민사소송 유무",
    )


class ComplaintFormSection8Other(BaseModel):
    """8. 기타."""

    content: str | None = Field(default=None, description="8. 기타 — 보충 사항")


class ComplaintFormSubmissionFooter(BaseModel):
    """제출일·서명·제출처(하단)."""

    date_year: int | None = Field(default=None, description="하단 — 제출일(년)")
    date_month: int | None = Field(default=None, description="하단 — 제출일(월)")
    date_day: int | None = Field(default=None, description="하단 — 제출일(일)")
    accuser_name: str | None = Field(default=None, description="하단 — 고소인 성명(인)")
    submitter_name: str | None = Field(default=None, description="하단 — 제출인 성명(인)")
    submission_target_police_station: str | None = Field(
        default=None,
        description="하단 — 제출처('○○ 귀중'의 경찰서·청 이름)",
    )


class ComplaintFormData(BaseModel):
    """고소장 폼(JSON). 서식 번호 1~8 순."""

    section_1_complainant: ComplaintFormSection1Complainant = Field(
        default_factory=ComplaintFormSection1Complainant,
        description="1. 고소인",
    )
    section_2_accused: ComplaintFormSection2Accused = Field(
        default_factory=ComplaintFormSection2Accused,
        description="2. 피고소인",
    )
    section_3_complaint_purpose: ComplaintFormSection3ComplaintPurpose = Field(
        default_factory=ComplaintFormSection3ComplaintPurpose,
        description="3. 고소 취지",
    )
    section_4_crime_facts: ComplaintFormSection4CrimeFacts = Field(
        default_factory=ComplaintFormSection4CrimeFacts,
        description="4. 범죄 사실",
    )
    section_5_complaint_reason: ComplaintFormSection5ComplaintReason = Field(
        default_factory=ComplaintFormSection5ComplaintReason,
        description="5. 고소 이유",
    )
    section_6_evidence: ComplaintFormSection6Evidence = Field(
        default_factory=ComplaintFormSection6Evidence,
        description="6. 증거 자료",
    )
    section_7_related_cases: ComplaintFormSection7RelatedCases = Field(
        default_factory=ComplaintFormSection7RelatedCases,
        description="7. 관련 사건",
    )
    section_8_other: ComplaintFormSection8Other = Field(
        default_factory=ComplaintFormSection8Other,
        description="8. 기타",
    )
    submission_footer: ComplaintFormSubmissionFooter = Field(
        default_factory=ComplaintFormSubmissionFooter,
        description="제출일·고소인/제출인·제출처",
    )


class StatementFormData(BaseModel):
    """스토킹 피해 사실 진술서 폼."""

    damage_facts_statement: str | None = Field(
        default=None,
        description="피해 사실 진술(필수 입력란 본문)",
    )
    date_year: int | None = Field(default=None, description="작성 일자 — 연(년)")
    date_month: int | None = Field(default=None, description="작성 일자 — 월")
    date_day: int | None = Field(default=None, description="작성 일자 — 일")
    declarant_name: str | None = Field(default=None, description="진술인 성명(인)")
    submission_target_police_station: str | None = Field(
        default=None,
        description="제출처 — 경찰서/청 이름('○○ 귀중'의 ○○)",
    )
