from typing import Dict, List
from .models import (
    SyllabusTopic,
    TextbookPage,
    Question,
    Answer,
    Evaluation,
    Student,
    ExamConfig,
    RubricMode,
)

# Simple in-memory "DB" for prototype
syllabus_topics: Dict[int, SyllabusTopic] = {}
textbook_pages: Dict[int, TextbookPage] = {}
questions: Dict[int, Question] = {}
answers: Dict[int, Answer] = {}
evaluations: Dict[int, Evaluation] = {}
students: Dict[int, Student] = {}
exam_configs: Dict[int, ExamConfig] = {}

# simple ID counters
_id_counters = {
    "topic": 0,
    "page": 0,
    "question": 0,
    "answer": 0,
    "evaluation": 0,
    "student": 0,
}

def _next_id(key: str) -> int:
    _id_counters[key] += 1
    return _id_counters[key]

def create_exam_config(exam_id: int, rubric_mode: RubricMode) -> ExamConfig:
    cfg = ExamConfig(exam_id=exam_id, rubric_mode=rubric_mode)
    exam_configs[exam_id] = cfg
    return cfg
