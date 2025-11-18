import tempfile
import json
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File
from ...core import db
from ...core.models import Student, Answer
from ...utils.pdf_utils import extract_pdf_text

router = APIRouter(prefix="/answer", tags=["answer"])


@router.post("/upload")
async def upload_student_answers(file: UploadFile = File(...)):
    """
    Upload student answers as PDF or JSON.
    
    JSON format expected:
    {
        "student_name": "John Doe",
        "student_roll": "S12345",
        "answers": [
            {"question_number": "1", "answer_text": "..."},
            {"question_number": "2", "answer_text": "..."}
        ]
    }
    
    PDF: Extract text and parse based on markers
    """
    if file.content_type == "application/json" or file.filename.endswith(".json"):
        # JSON format
        content = await file.read()
        data = json.loads(content)
        
        # Create or get student
        student_name = data.get("student_name", "Unknown")
        student_roll = data.get("student_roll", "UNKNOWN")
        
        student_id = db._next_id("student")
        student = Student(id=student_id, name=student_name, roll_no=student_roll)
        db.students[student_id] = student
        
        # Process answers
        answers_added = 0
        for ans_data in data.get("answers", []):
            q_num = ans_data.get("question_number", "")
            ans_text = ans_data.get("answer_text", "")
            
            # Find matching question
            question = None
            for q in db.questions.values():
                if q.question_number == str(q_num):
                    question = q
                    break
            
            if question:
                ans_id = db._next_id("answer")
                answer = Answer(
                    id=ans_id,
                    student_id=student_id,
                    question_id=question.id,
                    text=ans_text,
                    question_text=question.text
                )
                db.answers[ans_id] = answer
                answers_added += 1
        
        return {
            "student_id": student_id,
            "student_name": student_name,
            "student_roll": student_roll,
            "answers_added": answers_added
        }
    
    else:
        # PDF format
        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp.flush()
            text = extract_pdf_text(tmp.name)
        
        # Simple parsing: look for patterns like "Student Name:", "Roll No:", "Q1:", "Q2:" etc.
        lines = text.split('\n')
        student_name = "Unknown"
        student_roll = "UNKNOWN"
        current_q = None
        current_answer = []
        
        student_id = db._next_id("student")
        answers_added = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to extract student info
            if line.lower().startswith("student name:") or line.lower().startswith("name:"):
                student_name = line.split(":", 1)[1].strip()
            elif line.lower().startswith("roll no:") or line.lower().startswith("roll number:"):
                student_roll = line.split(":", 1)[1].strip()
            
            # Check for question markers
            elif line.lower().startswith("q") and ":" in line[:5]:
                # Save previous answer if exists
                if current_q and current_answer:
                    ans_text = " ".join(current_answer).strip()
                    # Find matching question
                    for q in db.questions.values():
                        if q.question_number == str(current_q):
                            ans_id = db._next_id("answer")
                            answer = Answer(
                                id=ans_id,
                                student_id=student_id,
                                question_id=q.id,
                                text=ans_text,
                                question_text=q.text
                            )
                            db.answers[ans_id] = answer
                            answers_added += 1
                            break
                
                # Start new question
                current_q = line.split(":")[0].replace("Q", "").replace("q", "").strip()
                current_answer = [line.split(":", 1)[1].strip() if ":" in line else ""]
            else:
                # Continue current answer
                if current_q:
                    current_answer.append(line)
        
        # Save last answer
        if current_q and current_answer:
            ans_text = " ".join(current_answer).strip()
            for q in db.questions.values():
                if q.question_number == str(current_q):
                    ans_id = db._next_id("answer")
                    answer = Answer(
                        id=ans_id,
                        student_id=student_id,
                        question_id=q.id,
                        text=ans_text,
                        question_text=q.text
                    )
                    db.answers[ans_id] = answer
                    answers_added += 1
                    break
        
        # Create student
        student = Student(id=student_id, name=student_name, roll_no=student_roll)
        db.students[student_id] = student
        
        return {
            "student_id": student_id,
            "student_name": student_name,
            "student_roll": student_roll,
            "answers_added": answers_added,
            "message": "PDF parsed successfully"
        }


@router.get("/list")
async def list_answers():
    """Get all uploaded answers"""
    result = []
    for ans in db.answers.values():
        student = db.students.get(ans.student_id)
        result.append({
            "answer_id": ans.id,
            "student_name": student.name if student else "Unknown",
            "student_roll": student.roll_no if student else "Unknown",
            "question_id": ans.question_id,
            "question_text": ans.question_text,
            "answer_preview": ans.text[:100] + "..." if len(ans.text) > 100 else ans.text
        })
    return {"answers": result, "total": len(result)}


@router.delete("/clear")
async def clear_answers():
    """Clear all answers and students"""
    db.answers.clear()
    db.students.clear()
    db.evaluations.clear()
    db._id_counters["answer"] = 0
    db._id_counters["student"] = 0
    db._id_counters["evaluation"] = 0
    return {"message": "All answers, students, and evaluations cleared"}
