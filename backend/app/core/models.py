from typing import List, Dict, Optional
from enum import Enum
from pydantic import BaseModel

# ---- Core domain models ----

class SyllabusTopic(BaseModel):
    id: int
    name: str
    description: str
    chapter: Optional[str] = None
    reference_book: Optional[str] = None


class TextbookPage(BaseModel):
    id: int
    book_name: str
    page_number: int
    text: str
    chapter: Optional[str] = None


class Question(BaseModel):
    id: int
    exam_id: int
    question_number: str
    text: str
    max_marks: float
    bloom_level: Optional[str] = None
    rubric: Optional[Dict] = None  # analytic rubric JSON
    model_answer: Optional[str] = None  # reference/ideal answer
    chapter: Optional[str] = None


class Answer(BaseModel):
    id: int
    student_id: int
    question_id: int
    text: str
    question_text: Optional[str] = None  # for reference


class Evaluation(BaseModel):
    id: int
    answer_id: int
    question_id: int
    score: float
    max_score: float
    feedback: str
    syllabus_topic_ids: List[int]
    textbook_refs: List[str]  # e.g. ["Book A, p.12", "Book B, p.45"]
    rubric_breakdown: Dict[str, float]
    model_answer_comparison: Optional[str] = None


class Student(BaseModel):
    id: int
    name: str
    roll_no: str


# ---- Config & rubric mode ----

class RubricMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class ExamConfig(BaseModel):
    exam_id: int
    rubric_mode: RubricMode = RubricMode.AUTO
