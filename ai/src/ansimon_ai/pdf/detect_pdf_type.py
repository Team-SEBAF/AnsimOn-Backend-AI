from typing import List, Tuple
import pdfplumber

def detect_pdf_type(pdf_path: str, min_text_length: int = 10) -> Tuple[str, int]:
    text_page_count = 0
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if len(text.strip()) >= min_text_length:
                text_page_count += 1
    if text_page_count > 0:
        return "text", text_page_count
    else:
        return "image", 0

def detect_pdf_page_types(pdf_path: str, min_text_length: int = 10) -> List[str]:
    page_types: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if len(text.strip()) >= min_text_length:
                page_types.append("text")
            else:
                page_types.append("image")
    return page_types