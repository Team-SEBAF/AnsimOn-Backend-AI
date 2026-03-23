from typing import List
from .detect_pdf_type import detect_pdf_page_types, detect_pdf_type
from .extract_text_pdf import extract_text_from_pdf, extract_text_from_pdf_page
from .extract_image_pdf import extract_text_from_image_pdf, extract_text_from_image_pdf_page

def extract_text_auto(pdf_path: str, lang: str = "kor") -> List[str]:
    pdf_type, _ = detect_pdf_type(pdf_path)
    if pdf_type == "text":
        page_types = detect_pdf_page_types(pdf_path)
        if all(page_type == "text" for page_type in page_types):
            return extract_text_from_pdf(pdf_path)

        texts: List[str] = []
        for page_index, page_type in enumerate(page_types):
            if page_type == "text":
                texts.append(extract_text_from_pdf_page(pdf_path, page_index))
            else:
                texts.append(extract_text_from_image_pdf_page(pdf_path, page_index, lang=lang))
        return texts
    else:
        page_types = detect_pdf_page_types(pdf_path)
        if all(page_type == "image" for page_type in page_types):
            return extract_text_from_image_pdf(pdf_path, lang=lang)

        texts = []
        for page_index, page_type in enumerate(page_types):
            if page_type == "text":
                texts.append(extract_text_from_pdf_page(pdf_path, page_index))
            else:
                texts.append(extract_text_from_image_pdf_page(pdf_path, page_index, lang=lang))
        return texts