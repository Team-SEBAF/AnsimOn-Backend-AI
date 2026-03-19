from dataclasses import dataclass
from typing import Optional, List
import unicodedata

@dataclass(frozen=True)
class EvidenceAnchor:
    start_char: int
    end_char: int

class AnchorMatcher:
    def match(
        self,
        *,
        full_text: str,
        evidence_span: Optional[str],
    ) -> Optional[EvidenceAnchor]:
        if not evidence_span:
            return None

        full = unicodedata.normalize("NFC", full_text)
        span = unicodedata.normalize("NFC", evidence_span).strip()
        if not span:
            return None

        matches: List[int] = []
        start = 0
        span_len = len(span)

        while True:
            idx = full.find(span, start)
            if idx == -1:
                break

            matches.append(idx)
            start = idx + 1

            if len(matches) > 1:
                return None

        if len(matches) != 1:
            return None

        start_char = matches[0]
        end_char = start_char + span_len

        return EvidenceAnchor(
            start_char=start_char,
            end_char=end_char,
        )