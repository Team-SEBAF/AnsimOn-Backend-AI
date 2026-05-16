import base64
import json
from pathlib import Path

from schemas.complaint_writing import ComplaintWritingAiInput
from ansimon_ai.structuring.types import StructuringInput
from ansimon_ai.video import ExtractedVideoFrame

PROMPT_PATH = Path(__file__).parent / "system_prompt_v0.txt"
COMPLAINT_DOCUMENT_PROMPT_PATH = (
    Path(__file__).parent / "complaint_document_system_prompt_v0.txt"
)
DAMAGE_FACTS_STATEMENT_PROMPT_PATH = (
    Path(__file__).parent / "damage_facts_statement_system_prompt_v0.txt"
)

def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")

def load_complaint_document_system_prompt() -> str:
    return COMPLAINT_DOCUMENT_PROMPT_PATH.read_text(encoding="utf-8")

def load_damage_facts_statement_system_prompt() -> str:
    return DAMAGE_FACTS_STATEMENT_PROMPT_PATH.read_text(encoding="utf-8")

def build_structuring_messages(struct_input: StructuringInput) -> list[dict]:
    segments_json = json.dumps(
        [seg.model_dump(mode="json") for seg in struct_input.segments],
        ensure_ascii=False,
        indent=2,
    )
    stt_section = _build_stt_context_section(struct_input)

    return [
        {
            "role": "system",
            "content": load_system_prompt(),
        },
        {
            "role": "user",
            "content": (
                f"{stt_section}"
                "### INPUT TEXT (anchor base)\n\n"
                f"{struct_input.full_text}\n\n"
                "### SEGMENTS (json)\n\n"
                f"{segments_json}"
            ),
        },
    ]

def _build_stt_context_section(struct_input: StructuringInput) -> str:
    if struct_input.source_type != "stt":
        return ""

    interpretation_note = (
        "### STT INTERPRETATION NOTE\n\n"
        "For call or conversation evidence, summarize the ordered flow of contact, "
        "pressure, refusal, warning, and response instead of replaying every line. "
        "Use `피해자` or `상대방` in the final Korean title/description when the role "
        "is clear; omit the subject only when it is unclear. Do not replace unclear "
        "subjects with analytic phrases such as `한쪽`, `응답 측`, or `전화를 건 측`. "
        "Do not infer the aggressor or threat evidence from swear words or reporting/"
        "legal warnings alone. If the call involves an unknown number, another number "
        "after blocking, or monitoring context, treat that as contact or block-bypass "
        "context before interpreting later warnings. Korean response phrases such as "
        "`신고한다`, `끝까지 간다`, or `고소한다` are possible defensive reporting/"
        "legal-response language in that context. Because STT text can contain "
        "misrecognitions, avoid direct quotation unless wording is short, clear, and "
        "important; summarize awkward phrases as `취지의 발언`, `표현`, or `언급`.\n\n"
    )
    voice_description_note = (
        "### VOICE DESCRIPTION NOTE\n\n"
        "For the final Korean title/description, do not use analytic wording such as "
        "`발화`, `한쪽`, `다른 쪽`, `한 사람`, `다른 사람`, `응답 측`, `발신 측`, "
        "`수신 측`, `전화를 건 측`, or `연락받은 쪽`. Use `피해자` and `상대방` when the call flow makes the roles "
        "clear. If someone continues contact by referencing blocked contact, no response, "
        "a changed number/account, another number, or other bypass of avoidance, treat "
        "that person as the contact-continuing `상대방` unless the input explicitly says "
        "the victim initiated that contact. Reporting/legal warnings or strong refusal "
        "against that continued contact may be the `피해자`'s defensive response. Center "
        "the summary on the bypassed/continued contact, monitoring/contextual pressure, "
        "and the other person's response. "
        "Do not title or describe a victim's defensive swear words or reporting warnings "
        "as the main incident. Summarize phrases like `신고한다` or `끝까지 간다` as "
        "`피해자가 신고하겠다는 대응을 했습니다` when they respond to prior contact "
        "or monitoring.\n\n"
    )

    if not any(segment.speaker for segment in struct_input.segments):
        return f"{interpretation_note}{voice_description_note}"

    note = (
        "### SPEAKER ATTRIBUTION NOTE\n\n"
        "Use speaker labels in INPUT TEXT and SEGMENTS as the primary source for "
        "speaker attribution. Same labels indicate the same speaker; different labels "
        "must not be merged into one continuous statement. Do not use raw labels in "
        "the final Korean summary.\n\n"
    )
    role_note = (
        "### SPEAKER ROLE CONSISTENCY NOTE\n\n"
        "Relationship terms and self-references such as senior, junior, freshman, "
        "sunbae, hoobae, `선배`, `후배`, `신입생`, `내가`, or `저는` belong only to "
        "the speaker label that said them. Do not combine a refusal from one speaker "
        "with another speaker's relationship justification. If ownership is unclear, "
        "omit the relationship label and describe the safer flow, such as contact "
        "refusal plus repeated requests for reasons. Avoid using relationship labels "
        "as grammatical subjects when the Korean sentence can be subjectless.\n\n"
    )
    single_speaker_note = _build_single_speaker_note(struct_input)
    transcript = _build_speaker_labeled_transcript(struct_input)
    if _full_text_has_speaker_labels(struct_input) or not transcript:
        return f"{interpretation_note}{voice_description_note}{note}{role_note}{single_speaker_note}"

    return (
        f"{interpretation_note}{voice_description_note}{note}{role_note}{single_speaker_note}"
        f"### SPEAKER-LABELED TRANSCRIPT (context only)\n\n{transcript}\n\n"
    )

def _build_single_speaker_note(struct_input: StructuringInput) -> str:
    speakers = {
        segment.speaker
        for segment in struct_input.segments
        if segment.speaker
    }
    if len(speakers) != 1:
        return ""

    return (
        "This STT input has one detected speaker only. Unless the input clearly says "
        "this is the victim's own voice memo, refer to this speaker as `상대방` in "
        "the final Korean summary. Do not use `화자`, `발화자`, `말한 사람`, or "
        "`한쪽`. Prioritize the overall contact or pressure flow over isolated swear "
        "words.\n\n"
    )

def _build_speaker_labeled_transcript(struct_input: StructuringInput) -> str:
    lines = []
    for segment in struct_input.segments:
        if not segment.speaker:
            continue
        start = f"{segment.start:.2f}"
        end = f"{segment.end:.2f}"
        lines.append(f"[{start}-{end}] {segment.speaker}: {segment.text}")

    return "\n".join(lines)

def _full_text_has_speaker_labels(struct_input: StructuringInput) -> bool:
    return any(
        segment.speaker and f"{segment.speaker}:" in struct_input.full_text
        for segment in struct_input.segments
    )

def build_complaint_document_messages(
    ai_input: ComplaintWritingAiInput,
) -> list[dict]:
    ai_input_json = json.dumps(ai_input.model_dump(mode="json"), ensure_ascii=False, indent=2)

    return [
        {
            "role": "system",
            "content": load_complaint_document_system_prompt(),
        },
        {
            "role": "user",
            "content": (
                "### STEP3 INPUT (json)\n\n"
                f"{ai_input_json}\n\n"
                "Write the complaint document sections strictly from the provided input."
            ),
        },
    ]

def build_damage_facts_statement_messages(
    ai_input: ComplaintWritingAiInput,
) -> list[dict]:
    ai_input_json = json.dumps(ai_input.model_dump(mode="json"), ensure_ascii=False, indent=2)

    return [
        {
            "role": "system",
            "content": load_damage_facts_statement_system_prompt(),
        },
        {
            "role": "user",
            "content": (
                "### STEP3 INPUT (json)\n\n"
                f"{ai_input_json}\n\n"
                "Write the damage facts statement strictly from the provided input."
            ),
        },
    ]

def build_victim_image_messages(
    *,
    image_bytes: bytes,
    file_name: str | None = None,
    file_format: str | None = None,
) -> list[dict]:
    mime_type = _infer_image_mime_type(file_name=file_name, file_format=file_format)
    data_url = _build_image_data_url(image_bytes=image_bytes, mime_type=mime_type)

    context_lines = [
        "Analyze this victim evidence image and return a JSON object that follows the required schema.",
        "Focus only on what is visually observable in the image.",
        "Do not make medical, legal, or factual conclusions beyond the image itself.",
        "If something is unclear, use cautious language and lower confidence.",
        "If the image suggests bruising, injury, physical force, or sexual misconduct, describe it as an observation only.",
        "If visible date or time text appears in the image, use it when relevant.",
        "Because this is an image-first input, evidence_span and evidence_anchor may be null when no reliable text span exists.",
        "For visible injury marks, describe only the visible bruise or discoloration itself, such as its body location, shape, and color. Do not mention fingers, hands, or nearby gestures, and do not add sentences saying the exact body part, cause, or timing cannot be confirmed.",
        "Assign the `physical` tag only when bodily injury marks, bruising, bleeding, restraint, or strong physical force are comparatively clear in the image.",
        "Do not assign the `physical` tag for simple touch or ambiguous contact alone.",
        "Assign the `sexual_insult` tag only when sexual exposure, sexual humiliation, or unwanted sexual contact is comparatively clear in the image.",
        "Do not assign the `sexual_insult` tag when the sexual context is unclear or inferred only from pose or proximity.",
    ]
    if file_name:
        context_lines.append(f"File name: {file_name}")

    return [
        {
            "role": "system",
            "content": load_system_prompt(),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "\n".join(context_lines),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": data_url,
                    },
                },
            ],
        },
    ]

def build_victim_video_messages(
    *,
    frames: list[ExtractedVideoFrame],
    file_name: str | None = None,
) -> list[dict]:
    content: list[dict] = [
        {
            "type": "text",
            "text": "\n".join(
                [
                    "Analyze these still images from the same victim evidence video and return a single JSON object that follows the required schema.",
                    "All images come from one video evidence, so produce one combined result for the whole video.",
                    "Focus only on what is visually observable across the images.",
                    "Do not make medical, legal, or factual conclusions beyond the video images themselves.",
                    "In the final Korean description, use natural Korean wording such as `장면` instead of `프레임` when referring to video content.",
                    "Describe only the main incident action and the person performing it. Do not describe background people, vehicles, objects, or nearby actions that are not directly part of the incident.",
                    "Do not use arrows, step-by-step notation, or diagram-like phrasing in the final Korean description. Describe the incident flow only in natural sentence form.",
                    "If something is unclear, use cautious language and lower confidence.",
                    "For visible injury marks, describe only the visible bruise or discoloration itself, such as its body location, shape, and color. Do not mention fingers, hands, or nearby gestures, and do not add sentences saying the exact body part, cause, or timing cannot be confirmed.",
                    "Assign the `physical` tag only when bodily injury marks, bruising, bleeding, restraint, or strong physical force are comparatively clear in the images.",
                    "Do not assign the `physical` tag for simple touch or ambiguous contact alone.",
                    "Assign the `sexual_insult` tag only when sexual exposure, sexual humiliation, or unwanted sexual contact is comparatively clear in the frames.",
                    "Do not assign the `sexual_insult` tag when the sexual context is unclear or inferred only from pose or proximity.",
                    "Because this is a video-image input, evidence_span and evidence_anchor may be null when no reliable text span exists.",
                    *( [f"File name: {file_name}"] if file_name else [] ),
                ]
            ),
        }
    ]

    for frame in frames:
        content.append(
            {
                "type": "text",
                "text": f"Scene at {frame.frame_timestamp_seconds} seconds",
            }
        )
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": _build_image_data_url(
                        image_bytes=frame.path.read_bytes(),
                        mime_type=_infer_image_mime_type(
                            file_name=frame.path.name,
                            file_format="IMAGE",
                        ),
                    ),
                },
            }
        )

    return [
        {
            "role": "system",
            "content": load_system_prompt(),
        },
        {
            "role": "user",
            "content": content,
        },
    ]

def _infer_image_mime_type(*, file_name: str | None, file_format: str | None) -> str:
    if file_name:
        suffix = Path(file_name).suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if suffix == ".png":
            return "image/png"
        if suffix == ".webp":
            return "image/webp"
        if suffix == ".gif":
            return "image/gif"

    if file_format == "IMAGE":
        return "image/jpeg"

    return "application/octet-stream"

def _build_image_data_url(*, image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"