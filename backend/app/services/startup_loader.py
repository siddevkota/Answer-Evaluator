# backend/app/services/startup_loader.py
import os
from ..core.config import get_settings
from ..core import db
from ..utils.pdf_utils import extract_pdf_text
from .vectorstore import textbook_store

def load_reference_textbook_if_needed() -> None:
    """
    Load and index the reference textbook once at startup.

    If pages already exist in db.textbook_pages, we assume it's already loaded.
    """
    if db.textbook_pages:
        print("[INFO] Reference textbook already loaded in memory.")
        return

    settings = get_settings()
    path = settings.REFERENCE_TEXTBOOK_PATH
    book_name = settings.REFERENCE_TEXTBOOK_NAME

    if not os.path.exists(path):
        print(f"[WARN] Reference textbook not found at: {path}")
        return

    print(f"[INFO] Loading reference textbook from: {path}")
    text = extract_pdf_text(path)

    # Split by form feed (\f) which separates pages
    chunks = text.split("\f") if "\f" in text else [text]
    
    # Filter out empty chunks
    chunks = [c.strip() for c in chunks if c.strip()]
    
    texts = []
    metas = []
    for i, chunk in enumerate(chunks, start=1):
        pid = db._next_id("page")
        page = db.TextbookPage(
            id=pid,
            book_name=book_name,
            page_number=i,
            text=chunk,
        )
        db.textbook_pages[pid] = page
        
        # Use first 3000 chars for embeddings (better context than 2000)
        texts.append(chunk[:3000])
        metas.append(
            {"type": "textbook_page", "page_id": pid, "book_name": book_name, "page_number": i}
        )

    textbook_store.add_texts(texts, metas)
    print(
        f"[INFO] Loaded {len(chunks)} pages for '{book_name}' "
        f"into textbook_store."
    )
