from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal

from sqlalchemy.orm import Session

from shared.core.aws import download_s3_object
from shared.core.settings import settings
from worker.models.evidences_model import (
    EvidenceIncidentLog,
    EvidenceIncidentLogFile,
    EvidenceIncidentLogFormData,
    EvidenceIncidentLogType,
    EvidenceMessage,
    EvidenceReportRecord,
    EvidenceVictim,
    EvidenceVoice,
)
from worker.timeline.schemas import (
    IncidentLogFormInput,
    TimelinePrototypeAiInput,
    TimelinePrototypeEvidenceInput,
)

# content_type → file_format 매핑 (type 무시, content_type만 사용)
CONTENT_TYPE_TO_FORMAT: dict[
    str, Literal["IMAGE", "AUDIO", "VIDEO", "PDF", "HWP", "DOCX", "TXT"]
] = {
    "image/jpeg": "IMAGE",
    "image/png": "IMAGE",
    "image/heic": "IMAGE",
    "image/heif": "IMAGE",
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
) -> list[tuple[float, TimelinePrototypeEvidenceInput, str | None]]:
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
                ),
                r.s3_key,
            )
        )
    return result


def _build_evidence_voices(
    db: Session, complaint_id
) -> list[tuple[float, TimelinePrototypeEvidenceInput, str | None]]:
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
                ),
                r.s3_key,
            )
        )
    return result


def _build_evidence_victims(
    db: Session, complaint_id
) -> list[tuple[float, TimelinePrototypeEvidenceInput, str | None]]:
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
                ),
                r.s3_key,
            )
        )
    return result


def _build_evidence_report_records(
    db: Session, complaint_id
) -> list[tuple[float, TimelinePrototypeEvidenceInput, str | None]]:
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
                ),
                r.s3_key,
            )
        )
    return result


def _build_evidence_incident_logs(
    db: Session, complaint_id
) -> list[tuple[float, TimelinePrototypeEvidenceInput, str | None]]:
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
                    ),
                    file_row.s3_key,
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
                )
            )
    return result


def build_ai_input(db: Session, complaint_id) -> TimelinePrototypeAiInput:
    """
    complaint_id로 DB 조회 → TimelinePrototypeAiInput 생성.
    S3 다운로드는 병렬 처리 후 file_bytes 설정.
    """
    all_evidences: list[tuple[float, TimelinePrototypeEvidenceInput, str | None]] = []
    all_evidences.extend(_build_evidence_messages(db, complaint_id))
    all_evidences.extend(_build_evidence_voices(db, complaint_id))
    all_evidences.extend(_build_evidence_victims(db, complaint_id))
    all_evidences.extend(_build_evidence_report_records(db, complaint_id))
    all_evidences.extend(_build_evidence_incident_logs(db, complaint_id))

    all_evidences.sort(key=lambda x: x[0])
    print("all_evidences:", [(ev.type, ev.evidence_id) for _, ev, _ in all_evidences])

    # local: 타입별 첫 번째만 사용
    if settings.env == "local":
        seen_types: set[str] = set()
        evidences_to_use: list[tuple[float, TimelinePrototypeEvidenceInput, str | None]] = []
        for item in all_evidences:
            ev = item[1]
            if ev.type not in seen_types:
                seen_types.add(ev.type)
                evidences_to_use.append(item)
    else:
        evidences_to_use = all_evidences

    evidences = [ev for _, ev, _ in evidences_to_use]
    s3_keys = [s3 for _, _, s3 in evidences_to_use]

    # S3 다운로드가 필요한 evidences (s3_key가 있는 것)
    to_download = [(i, s3) for i, s3 in enumerate(s3_keys) if s3 is not None]

    def _download_one(item: tuple[int, str]) -> tuple[int, bytes]:
        i, s3_key = item
        data = download_s3_object(settings.S3_BUCKET_NAME, s3_key)
        return (i, data)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_download_one, item): item for item in to_download}
        for future in as_completed(futures):
            i, data = future.result()
            evidences[i] = evidences[i].model_copy(update={"file_bytes": data})

    return TimelinePrototypeAiInput(complaint_id=complaint_id, evidences=evidences)
