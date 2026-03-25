import pdfplumber
from typing import List

def extract_text_from_pdf(pdf_path: str) -> List[str]:
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            texts.append(text)
    return texts

def extract_text_from_pdf_page(pdf_path: str, page_index: int) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_index]
        return page.extract_text() or ""