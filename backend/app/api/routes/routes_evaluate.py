from typing import Dict, Any, List
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter
from ...core import db
from ...core.models import RubricMode, Question, Answer, Evaluation
from ...services.vectorstore import syllabus_store, textbook_store
from ...services.llm import chat_completion

router = APIRouter(prefix="/evaluate", tags=["evaluate"])

# Thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=5)

def ensure_rubric_for_question(q: Question, exam_mode: RubricMode) -> Question:
    """Ensure question has a rubric, generating one if needed"""
    if exam_mode == RubricMode.MANUAL:
        if not q.rubric:
            # Generate default rubric for manual mode
            q.rubric = {
                "criteria": [
                    {"name": "Accuracy", "description": "Correctness of answer", "weight": q.max_marks * 0.5},
                    {"name": "Completeness", "description": "Coverage of key points", "weight": q.max_marks * 0.3},
                    {"name": "Clarity", "description": "Clear expression", "weight": q.max_marks * 0.2}
                ]
            }
        return q
    
    if q.rubric:
        return q

    # Auto-generate rubric using LLM
    sys_prompt = (
        "You are an expert exam grader. Generate a grading rubric for the given question. "
        "Return ONLY valid JSON with this structure: "
        '{"criteria": [{"name": "criterion_name", "description": "what to look for", "weight": numeric_value}]}. '
        f"The weights must sum to exactly {q.max_marks}."
    )
    user_prompt = f"Question: {q.text}\nMax marks: {q.max_marks}"
    
    if q.model_answer:
        user_prompt += f"\n\nModel Answer: {q.model_answer}"
    
    try:
        raw = chat_completion(sys_prompt, user_prompt, max_tokens=500)
        
        # Try to extract JSON from response
        rubric_data = None
        try:
            rubric_data = json.loads(raw)
        except:
            # Try to find JSON in markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
            if json_match:
                rubric_data = json.loads(json_match.group(1))
            else:
                # Try to find any JSON object
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    rubric_data = json.loads(json_match.group(0))
        
        if rubric_data:
            q.rubric = rubric_data
        else:
            raise ValueError("No valid JSON found")
    except:
        # Fallback rubric
        q.rubric = {
            "criteria": [
                {"name": "Accuracy", "description": "Correctness", "weight": q.max_marks * 0.6},
                {"name": "Completeness", "description": "Coverage", "weight": q.max_marks * 0.4}
            ]
        }
    
    db.questions[q.id] = q
    return q


def evaluate_answer_with_ai(q: Question, ans: Answer) -> Dict[str, Any]:
    """
    Evaluate an answer using AI, comparing with model answer and rubric.
    Returns: {score, feedback, rubric_breakdown, model_comparison}
    """
    # Build comprehensive prompt
    sys_prompt = (
        "You are an expert exam grader for engineering thermodynamics. "
        "Evaluate the student's answer carefully, comparing it with the model answer and rubric. "
        "Return ONLY valid JSON with this structure:\n"
        "{\n"
        '  "score": numeric_score,\n'
        '  "feedback": "detailed feedback string",\n'
        '  "rubric_breakdown": {"criterion_name": score_for_that_criterion, ...},\n'
        '  "model_comparison": "comparison with model answer"\n'
        "}"
    )
    
    user_prompt = f"Question: {q.text}\n\n"
    user_prompt += f"Max Marks: {q.max_marks}\n\n"
    
    if q.rubric:
        user_prompt += f"Grading Rubric: {json.dumps(q.rubric, indent=2)}\n\n"
    
    if q.model_answer:
        user_prompt += f"Model Answer: {q.model_answer}\n\n"
    
    user_prompt += f"Student Answer: {ans.text}\n\n"
    user_prompt += "Provide detailed evaluation with specific feedback on what was done well and what could be improved."
    
    try:
        raw = chat_completion(sys_prompt, user_prompt, max_tokens=800)
        
        # Try to extract JSON from response (in case it's wrapped in markdown)
        result = None
        
        # First try direct parsing
        try:
            result = json.loads(raw)
        except:
            # Try to find JSON in markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # Try to find any JSON object
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
        
        if not result:
            raise ValueError("No valid JSON found in response")
        
        # Ensure score doesn't exceed max
        result["score"] = min(float(result.get("score", 0)), q.max_marks)
        
        # Ensure all required fields exist
        result.setdefault("feedback", "No feedback provided")
        result.setdefault("rubric_breakdown", {})
        result.setdefault("model_comparison", "")
        
        return result
    except Exception as e:
        # Fallback simple evaluation
        return {
            "score": q.max_marks * 0.5,  # Give half marks as fallback
            "feedback": f"Automated evaluation encountered an error. Manual review recommended. Raw response: {raw[:200] if 'raw' in locals() else 'N/A'}. Error: {str(e)[:100]}",
            "rubric_breakdown": {},
            "model_comparison": "Unable to compare due to processing error."
        }

async def generate_rubric_async(q: Question, exam_mode: RubricMode) -> Question:
    """Async wrapper for rubric generation"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, ensure_rubric_for_question, q, exam_mode)


async def evaluate_answer_async(q: Question, ans: Answer) -> tuple:
    """Async wrapper for single answer evaluation with context search"""
    loop = asyncio.get_event_loop()
    
    # Run context searches and evaluation in parallel
    async def search_textbook():
        return await loop.run_in_executor(executor, textbook_store.search, ans.text, 1)
    
    async def search_syllabus():
        if len(syllabus_store.vectors) > 0:
            return await loop.run_in_executor(executor, syllabus_store.search, ans.text, 1)
        return []
    
    async def evaluate():
        return await loop.run_in_executor(executor, evaluate_answer_with_ai, q, ans)
    
    # Execute all three operations in parallel
    page_hits, topic_hits, eval_result = await asyncio.gather(
        search_textbook(),
        search_syllabus(),
        evaluate()
    )
    
    page_refs = [
        f"{h.get('book_name', 'Textbook')} p.{h.get('page_number', '?')}"
        for h in page_hits
    ]
    
    topic_ids = [h.get("topic_id") for h in topic_hits if "topic_id" in h]
    
    return eval_result, topic_ids, page_refs


@router.post("/run/{exam_id}")
async def run_evaluation(exam_id: int):
    """
    Run comprehensive evaluation for all answers in the exam.
    Uses AI to compare with model answers and apply rubrics.
    
    Optimizations:
    - Parallel rubric generation for all questions
    - Parallel evaluation of all answers
    - Concurrent context searches
    """
    cfg = db.exam_configs.get(exam_id)
    if not cfg:
        # Create default config
        cfg = db.create_exam_config(exam_id, RubricMode.AUTO)

    # Get all questions for this exam
    exam_questions = [q for q in db.questions.values() if q.exam_id == exam_id]
    
    # Pre-generate rubrics for all questions IN PARALLEL
    print(f"[INFO] Pre-generating rubrics for {len(exam_questions)} questions in parallel...")
    rubric_tasks = [generate_rubric_async(q, cfg.rubric_mode) for q in exam_questions]
    await asyncio.gather(*rubric_tasks)
    print(f"[INFO] All rubrics ready. Starting parallel evaluation...")

    # Get all answers for this exam
    exam_answers = []
    for ans in db.answers.values():
        q = db.questions.get(ans.question_id)
        if q and q.exam_id == exam_id:
            exam_answers.append((ans, q))
    
    print(f"[INFO] Evaluating {len(exam_answers)} answers in parallel...")
    
    # Evaluate all answers IN PARALLEL
    eval_tasks = [evaluate_answer_async(q, ans) for ans, q in exam_answers]
    eval_results = await asyncio.gather(*eval_tasks)
    
    # Create evaluation records
    created = 0
    for (ans, q), (eval_result, topic_ids, page_refs) in zip(exam_answers, eval_results):
        ev_id = db._next_id("evaluation")
        ev = Evaluation(
            id=ev_id,
            answer_id=ans.id,
            question_id=q.id,
            score=eval_result.get("score", 0),
            max_score=q.max_marks,
            feedback=eval_result.get("feedback", "No feedback available"),
            syllabus_topic_ids=topic_ids,
            textbook_refs=page_refs,
            rubric_breakdown=eval_result.get("rubric_breakdown", {}),
            model_answer_comparison=eval_result.get("model_comparison", "")
        )
        db.evaluations[ev_id] = ev
        created += 1
    
    print(f"[INFO] Successfully evaluated all {created} answers in parallel")

    return {
        "exam_id": exam_id,
        "evaluations_created": created,
        "rubric_mode": cfg.rubric_mode.value
    }


@router.post("/single/{answer_id}")
async def evaluate_single_answer(answer_id: int):
    """Evaluate a single answer"""
    ans = db.answers.get(answer_id)
    if not ans:
        return {"error": "Answer not found"}
    
    q = db.questions.get(ans.question_id)
    if not q:
        return {"error": "Question not found"}
    
    # Get or create exam config
    cfg = db.exam_configs.get(q.exam_id)
    if not cfg:
        cfg = db.create_exam_config(q.exam_id, RubricMode.AUTO)
    
    # Ensure rubric
    q = ensure_rubric_for_question(q, cfg.rubric_mode)
    
    # Find context
    topic_hits = syllabus_store.search(ans.text, k=2)
    page_hits = textbook_store.search(ans.text, k=2)
    topic_ids = [h.get("topic_id") for h in topic_hits if "topic_id" in h]
    page_refs = [f"{h.get('book_name', 'Textbook')}" for h in page_hits]
    
    # Evaluate
    eval_result = evaluate_answer_with_ai(q, ans)
    
    # Create or update evaluation
    existing_eval = None
    for ev in db.evaluations.values():
        if ev.answer_id == answer_id:
            existing_eval = ev
            break
    
    if existing_eval:
        ev_id = existing_eval.id
    else:
        ev_id = db._next_id("evaluation")
    
    ev = Evaluation(
        id=ev_id,
        answer_id=ans.id,
        question_id=q.id,
        score=eval_result.get("score", 0),
        max_score=q.max_marks,
        feedback=eval_result.get("feedback", ""),
        syllabus_topic_ids=topic_ids,
        textbook_refs=page_refs,
        rubric_breakdown=eval_result.get("rubric_breakdown", {}),
        model_answer_comparison=eval_result.get("model_comparison", "")
    )
    db.evaluations[ev_id] = ev
    
    return {
        "evaluation_id": ev_id,
        "answer_id": answer_id,
        "score": ev.score,
        "max_score": ev.max_score,
        "feedback": ev.feedback,
        "rubric_breakdown": ev.rubric_breakdown
    }


@router.get("/results/{student_id}")
async def get_student_results(student_id: int):
    """Get all evaluation results for a student"""
    student = db.students.get(student_id)
    if not student:
        return {"error": "Student not found"}
    
    # Get all answers for this student
    student_answers = [ans for ans in db.answers.values() if ans.student_id == student_id]
    
    results = []
    total_score = 0.0
    total_max = 0.0
    
    for ans in student_answers:
        # Find evaluation for this answer
        evaluation = None
        for ev in db.evaluations.values():
            if ev.answer_id == ans.id:
                evaluation = ev
                break
        
        if evaluation:
            q = db.questions.get(ans.question_id)
            results.append({
                "question_number": q.question_number if q else "?",
                "question_text": q.text if q else "Unknown",
                "answer_text": ans.text,
                "score": evaluation.score,
                "max_score": evaluation.max_score,
                "feedback": evaluation.feedback,
                "rubric_breakdown": evaluation.rubric_breakdown,
                "model_comparison": evaluation.model_answer_comparison
            })
            total_score += evaluation.score
            total_max += evaluation.max_score
    
    percentage = (total_score / total_max * 100) if total_max > 0 else 0
    
    return {
        "student_id": student_id,
        "student_name": student.name,
        "student_roll": student.roll_no,
        "total_score": round(total_score, 2),
        "total_max": round(total_max, 2),
        "percentage": round(percentage, 2),
        "results": results,
        "total_questions": len(results)
    }


@router.get("/list")
async def list_evaluations():
    """List all evaluations with summary"""
    result = []
    for ev in db.evaluations.values():
        ans = db.answers.get(ev.answer_id)
        student = db.students.get(ans.student_id) if ans else None
        q = db.questions.get(ev.question_id)
        
        result.append({
            "evaluation_id": ev.id,
            "student_name": student.name if student else "Unknown",
            "student_roll": student.roll_no if student else "Unknown",
            "question_number": q.question_number if q else "?",
            "score": ev.score,
            "max_score": ev.max_score,
            "percentage": round((ev.score / ev.max_score * 100) if ev.max_score > 0 else 0, 1)
        })
    
    return {"evaluations": result, "total": len(result)}
