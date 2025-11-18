from typing import Dict, Any
from fastapi import APIRouter
from ...core import db
from ...core.models import RubricMode, Question

router = APIRouter(prefix="/rubric", tags=["rubric"])

@router.post("/mode/{exam_id}")
async def set_rubric_mode(exam_id: int, mode: RubricMode):
    cfg = db.exam_configs.get(exam_id)
    if not cfg:
        cfg = db.create_exam_config(exam_id, mode)
    else:
        cfg.rubric_mode = mode
        db.exam_configs[exam_id] = cfg
    return {"exam_id": exam_id, "rubric_mode": cfg.rubric_mode}

@router.post("/manual/{question_id}")
async def set_manual_rubric(question_id: int, rubric: Dict[str, Any]):
    q: Question = db.questions.get(question_id)  # type: ignore
    if not q:
        return {"error": "Question not found"}
    q.rubric = rubric
    db.questions[question_id] = q
    return {"question_id": question_id, "rubric": rubric}
