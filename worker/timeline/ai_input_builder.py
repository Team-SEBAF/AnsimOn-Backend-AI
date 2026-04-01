from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal

from schemas.timeline_inputs import (
    IncidentLogFormInput,
    TimelinePrototypeAiInput,
    TimelinePrototypeEvidenceInput,
)
from sqlalchemy.orm import Session

from shared.core.aws import download_s3_object
from shared.core.settings import settings
from shared.models.evidences_model import (
    EvidenceIncidentLog,
    EvidenceIncidentLogFile,
    EvidenceIncidentLogFormData,
    EvidenceIncidentLogType,
    EvidenceMessage,
    EvidenceReportRecord,
    EvidenceVictim,
    EvidenceVoice,
)
from worker.heic_convert import heic_bytes_to_png

# content_type → file_format 매핑 (type 무시, content_type만 사용)
CONTENT_TYPE_TO_FORMAT: dict[
    str, Literal["IMAGE", "AUDIO", "VIDEO", "PDF", "HWP", "DOCX", "TXT"]
] = {
    "image/jpeg": "IMAGE",
    "image/png": "IMAGE",
    "image/heic": "IMAGE",
    "audio/mp4": "AUDIO",
    "audio/x-m4a": "AUDIO",
    "audio/mpeg": "AUDIO",
    "audio/wav": "AUDIO",
    "audio/x-wav": "AUDIO",
    "video/mp4": "VIDEO",
    "video/quicktime": "VIDEO",
    "application/pdf": "PDF",
    "application/msword": "DOCX",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
    "application/x-hwp": "HWP",
    "application/haansofthwp": "HWP",
    "application/vnd.hancom.hwp": "HWP",
    "text/plain": "TXT",
}


def _content_type_to_file_format(
    content_type: str,
) -> Literal["IMAGE", "AUDIO", "VIDEO", "PDF", "HWP", "DOCX", "TXT"] | None:
    return CONTENT_TYPE_TO_FORMAT.get(content_type)


def _build_evidence_messages(
    db: Session, complaint_id
) -> list[tuple[float, TimelinePrototypeEvidenceInput, str | None, str | None]]:
    """MESSAGE 타입 evidences."""
    rows = db.query(EvidenceMessage).filter(EvidenceMessage.complaint_id == complaint_id).all()
    result = []
    for r in rows:
        fmt = _content_type_to_file_format(r.content_type)
        if fmt is None:
            continue
        result.append(
            (
                r.created_at.timestamp(),
                TimelinePrototypeEvidenceInput(
                    evidence_id=r.message_id,
                    type="MESSAGE",
                    file_format=fmt,
                    file_name=r.filename,
                    extracted_text=None,
                    file_created_at=r.file_created_at,
                ),
                r.s3_key,
                r.content_type,
            )
        )
    return result


def _build_evidence_voices(
    db: Session, complaint_id
) -> list[tuple[float, TimelinePrototypeEvidenceInput, str | None, str | None]]:
    """VOICE 타입 evidences."""
    rows = db.query(EvidenceVoice).filter(EvidenceVoice.complaint_id == complaint_id).all()
    result = []
    for r in rows:
        fmt = _content_type_to_file_format(r.content_type)
        if fmt is None:
            continue
        result.append(
            (
                r.created_at.timestamp(),
                TimelinePrototypeEvidenceInput(
                    evidence_id=r.voice_id,
                    type="VOICE",
                    file_format=fmt,
                    file_name=r.filename,
                    extracted_text=None,
                    file_created_at=r.file_created_at,
                ),
                r.s3_key,
                r.content_type,
            )
        )
    return result


def _build_evidence_victims(
    db: Session, complaint_id
) -> list[tuple[float, TimelinePrototypeEvidenceInput, str | None, str | None]]:
    """VICTIM 타입 evidences."""
    rows = db.query(EvidenceVictim).filter(EvidenceVictim.complaint_id == complaint_id).all()
    result = []
    for r in rows:
        fmt = _content_type_to_file_format(r.content_type)
        if fmt is None:
            continue
        result.append(
            (
                r.created_at.timestamp(),
                TimelinePrototypeEvidenceInput(
                    evidence_id=r.victim_id,
                    type="VICTIM",
                    file_format=fmt,
                    file_name=r.filename,
                    extracted_text=None,
                    file_created_at=r.file_created_at,
                ),
                r.s3_key,
                r.content_type,
            )
        )
    return result


def _build_evidence_report_records(
    db: Session, complaint_id
) -> list[tuple[float, TimelinePrototypeEvidenceInput, str | None, str | None]]:
    """REPORT_RECORD 타입 evidences."""
    rows = (
        db.query(EvidenceReportRecord)
        .filter(EvidenceReportRecord.complaint_id == complaint_id)
        .all()
    )
    result = []
    for r in rows:
        fmt = _content_type_to_file_format(r.content_type)
        if fmt is None:
            continue
        result.append(
            (
                r.created_at.timestamp(),
                TimelinePrototypeEvidenceInput(
                    evidence_id=r.report_record_id,
                    type="REPORT_RECORD",
                    file_format=fmt,
                    file_name=r.filename,
                    extracted_text=None,
                    file_created_at=r.file_created_at,
                ),
                r.s3_key,
                r.content_type,
            )
        )
    return result


def _build_evidence_incident_logs(
    db: Session, complaint_id
) -> list[tuple[float, TimelinePrototypeEvidenceInput, str | None, str | None]]:
    """INCIDENT_LOG 타입 evidences. FILE / FORM_DATA 분기."""
    rows = (
        db.query(EvidenceIncidentLog).filter(EvidenceIncidentLog.complaint_id == complaint_id).all()
    )
    result = []
    for r in rows:
        if r.type == EvidenceIncidentLogType.FILE:
            file_row = (
                db.query(EvidenceIncidentLogFile)
                .filter(EvidenceIncidentLogFile.incident_log_id == r.incident_log_id)
                .first()
            )
            if not file_row:
                continue
            fmt = _content_type_to_file_format(file_row.content_type)
            if fmt is None:
                continue
            result.append(
                (
                    r.created_at.timestamp(),
                    TimelinePrototypeEvidenceInput(
                        evidence_id=r.incident_log_id,
                        type="INCIDENT_LOG",
                        file_format=fmt,
                        file_name=r.name,
                        extracted_text=None,
                        file_created_at=file_row.file_created_at,
                    ),
                    file_row.s3_key,
                    file_row.content_type,
                )
            )
        else:  # FORM_DATA
            form_row = (
                db.query(EvidenceIncidentLogFormData)
                .filter(EvidenceIncidentLogFormData.incident_log_id == r.incident_log_id)
                .first()
            )
            if not form_row:
                continue
            result.append(
                (
                    r.created_at.timestamp(),
                    TimelinePrototypeEvidenceInput(
                        evidence_id=r.incident_log_id,
                        type="INCIDENT_LOG",
                        file_format=None,
                        file_name=None,
                        extracted_text=None,
                        incident_log_form=IncidentLogFormInput(
                            title=r.name,
                            date=form_row.date.strftime("%Y-%m-%d"),
                            time=form_row.time.strftime("%H:%M"),
                            place=form_row.location,
                            situation=form_row.description,
                        ),
                    ),
                    None,
                    None,
                )
            )
    return result


def build_ai_input(db: Session, complaint_id) -> TimelinePrototypeAiInput:
    """
    complaint_id로 DB 조회 → TimelinePrototypeAiInput 생성.
    S3 다운로드는 병렬 처리 후 file_bytes 설정.
    """
    all_evidences: list[tuple[float, TimelinePrototypeEvidenceInput, str | None, str | None]] = []
    all_evidences.extend(_build_evidence_messages(db, complaint_id))
    all_evidences.extend(_build_evidence_voices(db, complaint_id))
    all_evidences.extend(_build_evidence_victims(db, complaint_id))
    all_evidences.extend(_build_evidence_report_records(db, complaint_id))
    all_evidences.extend(_build_evidence_incident_logs(db, complaint_id))

    all_evidences.sort(key=lambda x: x[0])

    # local: MESSAGE 타입만 최대 3개 (테스트용)
    if settings.env == "local":
        messages_only = [x for x in all_evidences if x[1].type == "MESSAGE"]
        evidences_to_use = messages_only[:3]
    else:
        evidences_to_use = all_evidences

    evidences = [ev for _, ev, _, _ in evidences_to_use]
    s3_keys = [s3 for _, _, s3, _ in evidences_to_use]
    source_content_types = [ct for _, _, _, ct in evidences_to_use]

    # S3 다운로드가 필요한 evidences (s3_key가 있는 것)
    to_download = [
        (i, s3_keys[i], source_content_types[i])
        for i in range(len(evidences))
        if s3_keys[i] is not None
    ]

    def _download_one(item: tuple[int, str, str | None]) -> tuple[int, bytes]:
        i, s3_key, content_type = item
        data = download_s3_object(settings.S3_BUCKET_NAME, s3_key)
        if content_type == "image/heic":
            data = heic_bytes_to_png(data)
        return (i, data)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_download_one, item): item for item in to_download}
        for future in as_completed(futures):
            i, data = future.result()
            evidences[i] = evidences[i].model_copy(update={"file_bytes": data})

    return TimelinePrototypeAiInput(complaint_id=complaint_id, evidences=evidences)
