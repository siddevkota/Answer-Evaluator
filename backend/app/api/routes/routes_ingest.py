import tempfile
from fastapi import APIRouter, UploadFile, File
from ...core import db
from ...core.models import RubricMode
from ...utils.pdf_utils import extract_pdf_text, simple_question_split
from ...services.vectorstore import syllabus_store, textbook_store
from ...services.llm import chat_completion

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/syllabus")
async def ingest_syllabus(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp.flush()
        text = extract_pdf_text(tmp.name)

    # To keep it tiny, treat each non-empty line as a potential topic
    lines = [l for l in text.splitlines() if l.strip()]
    texts = []
    metas = []
    for line in lines:
        tid = db._next_id("topic")
        topic = db.SyllabusTopic(
            id=tid,
            name=line[:80],
            description=line,
        )
        db.syllabus_topics[tid] = topic
        texts.append(line)
        metas.append({"type": "syllabus_topic", "topic_id": tid})

    syllabus_store.add_texts(texts, metas)
    return {"num_topics": len(db.syllabus_topics)}

@router.post("/textbook")
async def ingest_textbook(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp.flush()
        text = extract_pdf_text(tmp.name)

    # Minimal: treat each page-ish chunk as one "page"
    chunks = text.split("\f") if "\f" in text else [text]
    texts = []
    metas = []
    for i, chunk in enumerate(chunks, start=1):
        pid = db._next_id("page")
        page = db.TextbookPage(
            id=pid,
            book_name=file.filename or "Textbook",
            page_number=i,
            text=chunk,
        )
        db.textbook_pages[pid] = page
        texts.append(chunk[:2000])  # limit size
        metas.append(
            {"type": "textbook_page", "page_id": pid, "book_name": page.book_name}
        )

    textbook_store.add_texts(texts, metas)
    return {"num_pages": len(db.textbook_pages)}

@router.post("/exam")
async def ingest_exam(file: UploadFile = File(...), rubric_mode: RubricMode = RubricMode.AUTO):
    with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp.flush()
        text = extract_pdf_text(tmp.name)

    # create a simple exam id
    exam_id = 1
    db.create_exam_config(exam_id, rubric_mode)
    q_texts = simple_question_split(text)
    for idx, qt in enumerate(q_texts, start=1):
        qid = db._next_id("question")
        q = db.Question(
            id=qid,
            exam_id=exam_id,
            question_number=str(idx),
            text=qt,
            max_marks=5.0,  # placeholder, you can parse from text later
        )
        db.questions[qid] = q

    # If rubric mode is auto, we can lazily generate later, or here.
    # To keep code short, we do it later in evaluation route.
    return {"exam_id": exam_id, "num_questions": len(q_texts)}
