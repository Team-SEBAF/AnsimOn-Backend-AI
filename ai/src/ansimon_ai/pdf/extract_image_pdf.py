from typing import List
from pdf2image import convert_from_path
import pytesseract

def extract_text_from_image_pdf(pdf_path: str, lang: str = "kor") -> List[str]:
    images = convert_from_path(pdf_path)
    texts = []
    for img in images:
        text = pytesseract.image_to_string(img, lang=lang)
        texts.append(text)
    return texts