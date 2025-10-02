# This file parses PDF files to extract text using PyPDF.
from pypdf import PdfReader

# Parse PDF and return list of (page_number, text)
def parse_pdf(file_path: str):
    reader = PdfReader(file_path)
    texts = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text and page_text.strip():
            texts.append((i+1, page_text))
    return texts
