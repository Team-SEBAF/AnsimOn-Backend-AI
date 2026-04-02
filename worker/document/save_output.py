from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from shared.models.complaint_model import Complaint, ComplaintStep
from shared.models.document_model import (
    ComplaintFormData,
    ComplaintFormSection1Complainant,
    ComplaintFormSection3ComplaintPurpose,
    ComplaintFormSection4CrimeFacts,
    ComplaintFormSection5ComplaintReason,
    ComplaintFormSection6Evidence,
    ComplaintFormSubmissionFooter,
    Document,
    StatementFormData,
)
from worker.document.ai_generated_stub import DocumentAiGeneratedFields


def _format_birthdate(user_birthdate: Any) -> str | None:
    """
    'YYYY-MM-DD' str 또는 null → 주민란 앞자리 'YYMMDD-'. 예: 2000-01-01 → 000101-
    """
    if user_birthdate is None:
        return None
    s = str(user_birthdate).strip()
    if not s:
        return None
    try:
        d = date.fromisoformat(s[:10])
    except ValueError:
        return None
    return f"{d.year % 100:02d}{d.month:02d}{d.day:02d}-"


def _build_complaint_form_data(
    output: DocumentAiGeneratedFields,
    *,
    today: date,
    user_name: str,
    user_email: str,
    formatted_birthdate: str | None,
) -> ComplaintFormData:
    """
    AI 출력(3~6) + 1. 고소인(이름·이메일·주민앞자리) + 하단 고소인/제출인 성명 + 제출일.
    """
    return ComplaintFormData(
        section_1_complainant=ComplaintFormSection1Complainant(
            name_or_company=user_name,
            email=user_email,
            resident_or_corp_registration_number=formatted_birthdate,
        ),
        section_3_complaint_purpose=ComplaintFormSection3ComplaintPurpose(
            content=output.section_3_complaint_purpose_content,
        ),
        section_4_crime_facts=ComplaintFormSection4CrimeFacts(
            content=output.section_4_crime_facts_content,
        ),
        section_5_complaint_reason=ComplaintFormSection5ComplaintReason(
            content=output.section_5_complaint_reason_content,
        ),
        section_6_evidence=ComplaintFormSection6Evidence(
            has_evidence_beyond_statement=True,
            evidence_list_text=list(output.section_6_evidence_list_text),
        ),
        submission_footer=ComplaintFormSubmissionFooter(
            date_year=today.year,
            date_month=today.month,
            date_day=today.day,
            accuser_name=user_name,
            submitter_name=user_name,
            submission_target_police_station=None,
        ),
    )


def _build_statement_form_data(
    output: DocumentAiGeneratedFields,
    *,
    today: date,
    user_name: str,
) -> StatementFormData:
    return StatementFormData(
        damage_facts_statement=output.statement_damage_facts_statement,
        date_year=today.year,
        date_month=today.month,
        date_day=today.day,
        declarant_name=user_name,
        submission_target_police_station=None,
    )


def save_output(
    db: Session,
    *,
    complaint_id: UUID,
    output: DocumentAiGeneratedFields,
    message_body: dict[str, Any],
) -> UUID:
    """
    complaint_id 당 documents 행 1개: 기존이 있으면 삭제 후 삽입.
    저장 후 complaint.step = DOCUMENT.
    """
    user_name = str(message_body["user_name"]).strip()
    user_email = str(message_body["user_email"]).strip()
    formatted_birthdate = _format_birthdate(message_body["user_birthdate"])

    today = date.today()
    complaint_form = _build_complaint_form_data(
        output,
        today=today,
        user_name=user_name,
        user_email=user_email,
        formatted_birthdate=formatted_birthdate,
    )
    statement_form = _build_statement_form_data(output, today=today, user_name=user_name)

    complaint_payload = complaint_form.model_dump(mode="json")
    statement_payload = statement_form.model_dump(mode="json")

    existing = db.query(Document).filter(Document.complaint_id == complaint_id).one_or_none()
    if existing is not None:
        db.delete(existing)
        db.flush()

    doc = Document(
        complaint_id=complaint_id,
        complaint_form_data=complaint_payload,
        statement_form_data=statement_payload,
    )
    db.add(doc)
    db.flush()
    document_id = doc.id

    complaint = db.get(Complaint, complaint_id)
    complaint.step = ComplaintStep.DOCUMENT

    return document_id
