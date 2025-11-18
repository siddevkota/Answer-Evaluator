from typing import List
from pypdf import PdfReader

def extract_pdf_text(path: str) -> str:
    """Extract text from PDF, preserving page boundaries with form feed character"""
    reader = PdfReader(path)
    texts: List[str] = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    # Use form feed (\f) to preserve page breaks for proper chunking
    return "\f".join(texts)

def split_lines(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]

def simple_question_split(text: str) -> List[str]:
    """
    Very naive: split on lines starting with numbers like '1.', '2.' etc.
    Replace this with something smarter later.
    """
    lines = split_lines(text)
    questions: List[str] = []
    current: List[str] = []
    for line in lines:
        if line[:2].isdigit() and (line[1] == "." or line[2:4] == ".)"):
            # new question begins
            if current:
                questions.append(" ".join(current))
                current = []
        current.append(line)
    if current:
        questions.append(" ".join(current))
    return questions
