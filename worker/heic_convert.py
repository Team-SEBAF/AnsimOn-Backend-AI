"""S3에서 받은 HEIC 바이트 → PNG 바이트 (Pillow + pillow-heif)."""

from __future__ import annotations

import io

_HEIF_OPENER_REGISTERED = False


def _register_heif_opener() -> None:
    """HEIC 디코딩용 (HEIF 컨테이너 계열). pillow-heif가 PIL에 등록."""
    global _HEIF_OPENER_REGISTERED
    if _HEIF_OPENER_REGISTERED:
        return
    from pillow_heif import register_heif_opener

    register_heif_opener()
    _HEIF_OPENER_REGISTERED = True


def heic_bytes_to_png(data: bytes) -> bytes:
    """HEIC 디코드 후 PNG로 인코딩."""
    _register_heif_opener()
    from PIL import Image

    with Image.open(io.BytesIO(data)) as im:
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        out = io.BytesIO()
        im.save(out, format="PNG")
        return out.getvalue()
