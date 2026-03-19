from __future__ import annotations

from pathlib import Path
import shutil
from typing import List, Optional, Tuple

from ansimon_ai.eval.validator_adapter_v0 import StructuringValidatorV0
from ansimon_ai.structuring.anchor.matcher import AnchorMatcher
from ansimon_ai.structuring.from_stt import build_structuring_input_from_stt
from ansimon_ai.structuring.from_text import build_structuring_input_from_text
from ansimon_ai.structuring.run import run_structuring_pipeline
from ansimon_ai.structuring.tag_patterns import extract_tags_from_structuring_input
from ansimon_ai.structuring.types import StructuringInput

from .grouping import bucket_evidences_by_date_time, build_timeline_event_evidences
from .types import (
    EvidenceProcessingResult,
    TimelineDateItem,
    TimelineEvent,
    TimelineEvidenceItem,
    TimelinePrototypeAiInput,
    TimelinePrototypeEvidenceInput,
    TimelinePrototypeOutput,
)

DEFAULT_MODEL_VERSION = "prototype-v1"

UNSUPPORTED_TYPE_ERROR = "UNSUPPORTED_EVIDENCE_TYPE"
UNSUPPORTED_FORMAT_ERROR = "UNSUPPORTED_FILE_FORMAT"
MISSING_INPUT_ERROR = "MISSING_EVIDENCE_INPUT"
MISSING_DEPENDENCY_ERROR = "MISSING_DEPENDENCY"
FILE_READ_ERROR = "FILE_READ_ERROR"
STRUCTURING_ERROR = "STRUCTURING_ERROR"

def build_timeline_prototype(
    ai_input: TimelinePrototypeAiInput,
    *,
    llm_client,
    anchor_matcher: Optional[AnchorMatcher] = None,
    validator: Optional[StructuringValidatorV0] = None,
    stt_engine=None,
    ocr_runner=None,
    cache: Optional[object] = None,
    model_version: str = DEFAULT_MODEL_VERSION,
) -> TimelinePrototypeOutput:
    if anchor_matcher is None:
        anchor_matcher = AnchorMatcher()
    if validator is None:
        validator = StructuringValidatorV0()

    evidence_results: List[EvidenceProcessingResult] = []

    for evidence in ai_input.evidences:
        result = process_single_evidence(
            evidence,
            llm_client=llm_client,
            anchor_matcher=anchor_matcher,
            validator=validator,
            stt_engine=stt_engine,
            ocr_runner=ocr_runner,
            cache=cache,
        )
        evidence_results.append(result)

    items = _assemble_timeline_items(evidence_results)
    return TimelinePrototypeOutput(
        items=items,
        model_version=model_version,
        evidence_results=evidence_results,
    )

def process_single_evidence(
    evidence: TimelinePrototypeEvidenceInput,
    *,
    llm_client,
    anchor_matcher: Optional[AnchorMatcher] = None,
    validator: Optional[StructuringValidatorV0] = None,
    stt_engine=None,
    ocr_runner=None,
    cache: Optional[object] = None,
) -> EvidenceProcessingResult:
    if evidence.type == "VICTIM":
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="skipped",
            error_code=UNSUPPORTED_TYPE_ERROR,
            error_message="VICTIM evidence is not supported in prototype-1.",
        )

    if anchor_matcher is None:
        anchor_matcher = AnchorMatcher()
    if validator is None:
        validator = StructuringValidatorV0()

    temp_dir = _create_runtime_temp_dir(evidence) if evidence.file_bytes is not None else None

    try:
        struct_input, source_type = _prepare_structuring_input(
            evidence,
            stt_engine=stt_engine,
            ocr_runner=ocr_runner,
            temp_dir=temp_dir,
        )
    except NotImplementedError as exc:
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="skipped",
            error_code=UNSUPPORTED_FORMAT_ERROR,
            error_message=str(exc),
        )
    except ModuleNotFoundError as exc:
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="failed",
            error_code=MISSING_DEPENDENCY_ERROR,
            error_message=f"Missing dependency: {exc.name}",
        )
    except (FileNotFoundError, OSError) as exc:
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="failed",
            error_code=FILE_READ_ERROR,
            error_message=str(exc),
        )
    except ValueError as exc:
        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="skipped",
            error_code=MISSING_INPUT_ERROR,
            error_message=str(exc),
        )
    try:
        try:
            structuring_result = run_structuring_pipeline(
                input=struct_input,
                llm_client=llm_client,
                anchor_matcher=anchor_matcher,
                validator=validator,
                cache=cache,
            )
        except Exception as exc:
            return EvidenceProcessingResult(
                evidence_id=evidence.evidence_id,
                type=evidence.type,
                status="failed",
                source_type=source_type,
                normalized_text=struct_input.full_text,
                error_code=STRUCTURING_ERROR,
                error_message=str(exc),
            )

        normalized_text = struct_input.full_text.strip()
        title = _build_title(evidence)
        description = _build_description(evidence, normalized_text)
        tags = extract_tags_from_structuring_input(struct_input)
        timestamp = _extract_primary_timestamp(struct_input)

        return EvidenceProcessingResult(
            evidence_id=evidence.evidence_id,
            type=evidence.type,
            status="completed",
            source_type=source_type,
            normalized_text=normalized_text,
            structured_data=structuring_result.output_json,
            timestamp=timestamp,
            title=title,
            description=description,
            tags=tags,
        )
    finally:
        if temp_dir is not None:
            try:
                shutil.rmtree(temp_dir)
            except OSError:
                pass

def _prepare_structuring_input(
    evidence: TimelinePrototypeEvidenceInput,
    *,
    stt_engine=None,
    ocr_runner=None,
    temp_dir: Optional[Path],
) -> Tuple[StructuringInput, str]:
    if evidence.type == "INCIDENT_LOG":
        if evidence.incident_log_form is not None:
            text = _incident_log_to_text(evidence)
            return build_structuring_input_from_text(text), "form"

    if evidence.extracted_text:
        return _prepare_structuring_input_from_extracted_text(evidence)

    input_path = _materialize_input_file(evidence, temp_dir=temp_dir)

    if evidence.type == "MESSAGE":
        return _prepare_message_from_file(evidence, input_path, ocr_runner=ocr_runner)

    if evidence.type == "VOICE":
        return _prepare_voice_from_file(
            evidence,
            input_path,
            stt_engine=stt_engine,
            ocr_runner=ocr_runner,
        )

    if evidence.type == "REPORT_RECORD":
        return _prepare_report_record_from_file(evidence, input_path)

    if evidence.type == "INCIDENT_LOG":
        return _prepare_incident_log_from_file(evidence, input_path)

    raise NotImplementedError(f"{evidence.type} is not supported in prototype-1.")

def _prepare_structuring_input_from_extracted_text(
    evidence: TimelinePrototypeEvidenceInput,
) -> Tuple[StructuringInput, str]:
    text = (evidence.extracted_text or "").strip()
    if not text:
        raise ValueError("extracted_text is empty.")

    if evidence.type == "INCIDENT_LOG":
        return _build_document_structuring_input(text), "document"

    if evidence.type == "REPORT_RECORD":
        return _build_document_structuring_input(text), "document"

    if evidence.type == "VOICE" and evidence.file_format == "AUDIO":
        return build_structuring_input_from_text(text), "stt"

    if evidence.type in {"MESSAGE", "VOICE"} and evidence.file_format == "IMAGE":
        return build_structuring_input_from_text(text), "ocr"

    if evidence.type == "VOICE":
        return build_structuring_input_from_text(text), "stt"

    return build_structuring_input_from_text(text), "document"

def _prepare_message_from_file(
    evidence: TimelinePrototypeEvidenceInput,
    input_path: str,
    *,
    ocr_runner=None,
) -> Tuple[StructuringInput, str]:
    if evidence.file_format != "IMAGE":
        raise NotImplementedError("MESSAGE supports IMAGE only in prototype-1.")

    from ansimon_ai.ocr.from_ocr import build_structuring_input_from_ocr

    ocr_result = _run_ocr(input_path, ocr_runner=ocr_runner)
    return build_structuring_input_from_ocr(ocr_result), "ocr"

def _prepare_voice_from_file(
    evidence: TimelinePrototypeEvidenceInput,
    input_path: str,
    *,
    stt_engine=None,
    ocr_runner=None,
) -> Tuple[StructuringInput, str]:
    if evidence.file_format == "IMAGE":
        from ansimon_ai.ocr.from_ocr import build_structuring_input_from_ocr

        ocr_result = _run_ocr(input_path, ocr_runner=ocr_runner)
        return build_structuring_input_from_ocr(ocr_result), "ocr"

    if evidence.file_format == "AUDIO":
        stt_result = _run_stt(input_path, stt_engine=stt_engine)
        return build_structuring_input_from_stt(stt_result), "stt"

    raise NotImplementedError("VOICE supports AUDIO or IMAGE only in prototype-1.")

def _prepare_report_record_from_file(
    evidence: TimelinePrototypeEvidenceInput,
    input_path: str,
) -> Tuple[StructuringInput, str]:
    return _prepare_document_evidence_from_file(
        evidence,
        input_path,
        unsupported_hwp_message="HWP report records are not supported yet.",
        unsupported_default_message=(
            "REPORT_RECORD supports extracted_text for all formats, and direct file "
            "handling for PDF, TXT, or DOCX only in prototype-1."
        ),
    )

def _prepare_incident_log_from_file(
    evidence: TimelinePrototypeEvidenceInput,
    input_path: str,
) -> Tuple[StructuringInput, str]:
    return _prepare_document_evidence_from_file(
        evidence,
        input_path,
        unsupported_hwp_message="HWP incident logs are not supported yet.",
        unsupported_default_message=(
            "INCIDENT_LOG supports incident_log_form or direct file handling for PDF, "
            "TXT, or DOCX only in prototype-1."
        ),
    )

def _prepare_document_evidence_from_file(
    evidence: TimelinePrototypeEvidenceInput,
    input_path: str,
    *,
    unsupported_hwp_message: str,
    unsupported_default_message: str,
) -> Tuple[StructuringInput, str]:
    if evidence.file_format == "PDF":
        from ansimon_ai.pdf.document_structuring import build_structuring_input_from_document
        from ansimon_ai.pdf.extract_text_auto import extract_text_auto

        texts = extract_text_auto(input_path)
        return build_structuring_input_from_document(texts), "document"

    if evidence.file_format == "TXT":
        text = Path(input_path).read_text(encoding="utf-8")
        return _build_document_structuring_input(text), "document"

    if evidence.file_format == "DOCX":
        from ansimon_ai.pdf.extract_text_docx import extract_text_from_docx

        text = extract_text_from_docx(input_path)
        if not text.strip():
            raise ValueError("DOCX text extraction returned empty text.")
        return _build_document_structuring_input(text), "document"

    if evidence.file_format == "HWP":
        raise NotImplementedError(unsupported_hwp_message)

    raise NotImplementedError(unsupported_default_message)

def _build_document_structuring_input(text: str) -> StructuringInput:
    from ansimon_ai.pdf.document_structuring import build_structuring_input_from_document

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        lines = [text]
    return build_structuring_input_from_document(lines)

def _run_ocr(image_path: str, *, ocr_runner=None):
    if ocr_runner is not None:
        return ocr_runner(image_path)

    from ansimon_ai.ocr.from_ocr import ocr_image_to_result

    return ocr_image_to_result(image_path)

def _run_stt(audio_path: str, *, stt_engine=None):
    if stt_engine is not None:
        return stt_engine.transcribe(audio_path)

    from ansimon_ai.stt.whisper_stt import WhisperSTT

    return WhisperSTT().transcribe(audio_path)

def _materialize_input_file(evidence: TimelinePrototypeEvidenceInput, *, temp_dir: Path) -> str:
    if evidence.file_bytes is None:
        raise ValueError("file_bytes or extracted_text is required for this evidence.")

    file_name = _resolve_temp_file_name(evidence)
    file_path = temp_dir / file_name
    file_path.write_bytes(evidence.file_bytes)
    return str(file_path)

def _resolve_temp_file_name(evidence: TimelinePrototypeEvidenceInput) -> str:
    if evidence.file_name:
        return Path(evidence.file_name).name

    suffix = _default_suffix_for_format(evidence.file_format)
    return f"{evidence.evidence_id}{suffix}"

def _default_suffix_for_format(file_format: Optional[str]) -> str:
    mapping = {
        "IMAGE": ".jpg",
        "AUDIO": ".wav",
        "VIDEO": ".mp4",
        "PDF": ".pdf",
        "HWP": ".hwp",
        "DOCX": ".docx",
        "TXT": ".txt",
    }
    return mapping.get(file_format or "", ".bin")

def _create_runtime_temp_dir(evidence: TimelinePrototypeEvidenceInput) -> Path:
    temp_dir = Path("data") / "_timeline_runtime_tmp" / str(evidence.evidence_id)
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

def _incident_log_to_text(evidence: TimelinePrototypeEvidenceInput) -> str:
    form = evidence.incident_log_form
    assert form is not None
    return "\n".join(
        [
            f"제목: {form.title}",
            f"날짜: {form.date}",
            f"시간: {form.time}",
            f"장소: {form.place}",
            f"상황: {form.situation}",
        ]
    )

def _build_title(evidence: TimelinePrototypeEvidenceInput) -> str:
    if evidence.type == "INCIDENT_LOG" and evidence.incident_log_form is not None:
        return evidence.incident_log_form.title

    mapping = {
        "MESSAGE": "메신저/문자 증거",
        "VOICE": "통화/음성 증거",
        "REPORT_RECORD": "신고/상담 기록",
        "INCIDENT_LOG": "사건 일지",
    }
    return mapping.get(evidence.type, evidence.type)

def _build_description(
    evidence: TimelinePrototypeEvidenceInput,
    normalized_text: str,
    *,
    limit: int = 280,
) -> str:
    text = normalized_text.strip()
    if not text:
        fallback = evidence.file_name or str(evidence.evidence_id)
        return fallback

    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."

def _extract_primary_timestamp(struct_input: StructuringInput):
    for segment in struct_input.segments:
        if segment.timestamp is not None:
            return segment.timestamp
    return None

def _assemble_timeline_items(
    evidence_results: List[EvidenceProcessingResult],
) -> List[TimelineDateItem]:
    completed = [result for result in evidence_results if result.status == "completed"]
    if not completed:
        return []

    flat_evidences = [
        {
            "evidence_id": result.evidence_id,
            "evidence_type": result.type,
            "timestamp": result.timestamp,
            "title": result.title or str(result.evidence_id),
            "description": result.description or "",
            "tags": list(result.tags),
        }
        for result in completed
    ]

    buckets = bucket_evidences_by_date_time(flat_evidences)
    by_date: dict[str, List[TimelineEvent]] = {}

    for date_str, time_str in _sorted_bucket_keys(buckets):
        grouped = build_timeline_event_evidences(buckets[(date_str, time_str)])
        event = TimelineEvent(
            time=time_str,
            evidences=[TimelineEvidenceItem(**item) for item in grouped],
        )
        by_date.setdefault(date_str, []).append(event)

    return [TimelineDateItem(date=date, events=events) for date, events in by_date.items()]

def _sorted_bucket_keys(buckets):
    return sorted(
        buckets.keys(),
        key=lambda item: (_date_sort_key(item[0]), item[1]),
    )

def _date_sort_key(date_str: str):
    if date_str == "UNKNOWN":
        return (1, date_str)
    return (0, date_str)
