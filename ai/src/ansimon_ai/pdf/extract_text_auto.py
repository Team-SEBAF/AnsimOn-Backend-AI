from typing import List
from .detect_pdf_type import detect_pdf_type
from .extract_text_pdf import extract_text_from_pdf
from .extract_image_pdf import extract_text_from_image_pdf

def extract_text_auto(pdf_path: str, lang: str = "kor") -> List[str]:
    pdf_type, _ = detect_pdf_type(pdf_path)
    if pdf_type == "text":
        return extract_text_from_pdf(pdf_path)
    else:
        return extract_text_from_image_pdf(pdf_path, lang=lang)