from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from shared.models.complaint_model import Complaint, ComplaintStep
from shared.models.document_model import (
    ComplaintFormData,
    ComplaintFormSection3ComplaintPurpose,
    ComplaintFormSection4CrimeFacts,
    ComplaintFormSection5ComplaintReason,
    ComplaintFormSection6Evidence,
    ComplaintFormSubmissionFooter,
    Document,
    StatementFormData,
)
from worker.document.ai_generated_stub import DocumentAiGeneratedFields

logger = logging.getLogger(__name__)


def _build_complaint_form_data(
    output: DocumentAiGeneratedFields,
    *,
    today: date,
) -> ComplaintFormData:
    """
    AI 출력(3~6) + 제출일 등 백엔드 자동값 + 나머지 None/기본.
    """
    # 전달하지 않은 필드는, 키는 있고 값은 None 으로 채워짐
    return ComplaintFormData(
        section_3_complaint_purpose=ComplaintFormSection3ComplaintPurpose(
            content=output.section_3_complaint_purpose_content,
        ),
        section_4_crime_facts=ComplaintFormSection4CrimeFacts(
            content=output.section_4_crime_facts_content,
            closing_summary=output.section_4_crime_facts_closing_summary,
        ),
        section_5_complaint_reason=ComplaintFormSection5ComplaintReason(
            content=output.section_5_complaint_reason_content,
            closing_summary=output.section_5_complaint_reason_closing_summary,
        ),
        section_6_evidence=ComplaintFormSection6Evidence(
            has_evidence_beyond_statement=True,
            evidence_list_text=list(output.section_6_evidence_list_text),
        ),
        submission_footer=ComplaintFormSubmissionFooter(
            date_year=today.year,
            date_month=today.month,
            date_day=today.day,
            # TODO: Cognito 연동 후
            accuser_name=None,
            submitter_name=None,
            submission_target_police_station=None,
        ),
    )


def _build_statement_form_data(
    output: DocumentAiGeneratedFields,
    *,
    today: date,
) -> StatementFormData:
    return StatementFormData(
        damage_facts_statement=output.statement_damage_facts_statement,
        date_year=today.year,
        date_month=today.month,
        date_day=today.day,
        # TODO: Cognito 연동 후
        declarant_name=None,
        submission_target_police_station=None,
    )


def save_output(
    db: Session,
    *,
    complaint_id: UUID,
    output: DocumentAiGeneratedFields,
) -> UUID:
    """
    complaint_id 당 documents 행 1개: 기존이 있으면 삭제 후 삽입.
    저장 후 complaint.step = DOCUMENT.
    """
    today = date.today()
    complaint_form = _build_complaint_form_data(output, today=today)
    statement_form = _build_statement_form_data(output, today=today)

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
