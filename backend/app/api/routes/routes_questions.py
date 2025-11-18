import json
import re
from typing import List, Dict, Any
from fastapi import APIRouter
from ...core import db
from ...core.models import Question
from ...utils.pdf_utils import extract_pdf_text
from ...core.config import get_settings

router = APIRouter(prefix="/questions", tags=["questions"])


def parse_qa_json_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """Extract and parse QA data from PDF"""
    text = extract_pdf_text(pdf_path)
    
    # Try to find JSON structure in the text
    # Look for { "chapters": pattern
    json_start = text.find('{"chapters"')
    if json_start == -1:
        json_start = text.find('{  "chapters"')
    if json_start == -1:
        json_start = text.find('{ "chapters"')
    
    if json_start != -1:
        # Find the closing brace
        json_text = text[json_start:]
        try:
            # Try to extract complete JSON
            data = json.loads(json_text)
            return data
        except:
            pass
    
    # Fallback: try to load from the actual JSON file if PDF parsing fails
    settings = get_settings()
    json_path = "data/QA.json"
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except:
        return {"chapters": []}


@router.post("/load-from-qa")
async def load_questions_from_qa(exam_id: int = 1):
    """
    Load questions from QA_generated.pdf or QA.json
    Creates questions with model answers from the structured data
    """
    settings = get_settings()
    qa_pdf_path = "data/QA_generated.pdf"
    
    # Parse QA data
    qa_data = parse_qa_json_from_pdf(qa_pdf_path)
    
    questions_added = 0
    q_number = 1
    
    for chapter in qa_data.get("chapters", []):
        chapter_num = chapter.get("chapter_number", 0)
        chapter_title = chapter.get("chapter_title", "Unknown Chapter")
        
        # Process short answer questions
        for sq in chapter.get("short_answer_questions", []):
            q_id = db._next_id("question")
            question = Question(
                id=q_id,
                exam_id=exam_id,
                question_number=str(q_number),
                text=sq.get("question", ""),
                max_marks=5.0,  # Default for short answer
                model_answer=sq.get("model_answer", ""),
                chapter=f"Chapter {chapter_num}: {chapter_title}",
                bloom_level="short"
            )
            db.questions[q_id] = question
            questions_added += 1
            q_number += 1
        
        # Process long answer questions
        for lq in chapter.get("long_answer_questions", []):
            q_id = db._next_id("question")
            question = Question(
                id=q_id,
                exam_id=exam_id,
                question_number=str(q_number),
                text=lq.get("question", ""),
                max_marks=10.0,  # Default for long answer
                model_answer=lq.get("model_answer", ""),
                chapter=f"Chapter {chapter_num}: {chapter_title}",
                bloom_level="long"
            )
            db.questions[q_id] = question
            questions_added += 1
            q_number += 1
    
    return {
        "exam_id": exam_id,
        "questions_loaded": questions_added,
        "chapters_processed": len(qa_data.get("chapters", []))
    }


@router.get("/list")
async def list_questions():
    """Get all loaded questions"""
    result = []
    for q in db.questions.values():
        result.append({
            "id": q.id,
            "question_number": q.question_number,
            "text": q.text[:100] + "..." if len(q.text) > 100 else q.text,
            "max_marks": q.max_marks,
            "chapter": q.chapter,
            "has_model_answer": bool(q.model_answer),
            "has_rubric": bool(q.rubric)
        })
    return {"questions": result, "total": len(result)}


@router.get("/{question_id}")
async def get_question_detail(question_id: int):
    """Get full details of a specific question"""
    q = db.questions.get(question_id)
    if not q:
        return {"error": "Question not found"}
    
    return {
        "id": q.id,
        "question_number": q.question_number,
        "text": q.text,
        "max_marks": q.max_marks,
        "chapter": q.chapter,
        "bloom_level": q.bloom_level,
        "model_answer": q.model_answer,
        "rubric": q.rubric
    }


@router.delete("/clear")
async def clear_questions():
    """Clear all questions"""
    db.questions.clear()
    db._id_counters["question"] = 0
    return {"message": "All questions cleared"}
