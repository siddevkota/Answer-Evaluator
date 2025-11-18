from typing import List
import csv
import io
from fastapi import APIRouter
from fastapi.responses import Response, StreamingResponse, HTMLResponse
from ...core import db
from ...core.models import Student, Evaluation, Question

router = APIRouter(prefix="/reports", tags=["reports"])

# Try to import WeasyPrint for PDF generation, fallback to HTML only
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except:
    WEASYPRINT_AVAILABLE = False
    print("[WARN] WeasyPrint not available. PDF generation disabled. Install system dependencies for PDF support.")


@router.get("/student/{student_id}/pdf")
async def generate_student_pdf_report(student_id: int):
    """Generate PDF report for a student"""
    if not WEASYPRINT_AVAILABLE:
        return {
            "error": "PDF generation not available",
            "message": "WeasyPrint system dependencies not installed. Use HTML report instead.",
            "install_instructions": "Install: brew install pango libffi (on macOS) or sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 (on Linux)"
        }
    
    student = db.students.get(student_id)
    if not student:
        return {"error": "Student not found"}
    
    # Get all evaluations for this student
    student_evals = []
    for ev in db.evaluations.values():
        ans = db.answers.get(ev.answer_id)
        if ans and ans.student_id == student_id:
            student_evals.append(ev)
    
    if not student_evals:
        return {"error": "No evaluations found for this student"}
    
    # Build questions map
    questions_by_id = {q.id: q for q in db.questions.values()}
    
    # Generate HTML
    html = render_student_report_html_enhanced(student, student_evals, questions_by_id)
    
    # Convert to PDF with proper encoding
    try:
        # Ensure HTML is properly encoded
        pdf_bytes = HTML(string=html, encoding='utf-8').write_pdf()
        
        # Verify PDF was generated successfully
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise ValueError("Generated PDF is empty")
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_{student.roll_no}.pdf",
                "Content-Length": str(len(pdf_bytes))
            }
        )
    except Exception as e:
        import traceback
        return {
            "error": f"PDF generation failed: {str(e)}",
            "details": traceback.format_exc()
        }


@router.get("/student/{student_id}/html", response_class=HTMLResponse)
async def generate_student_html_report(student_id: int):
    """Generate HTML report for a student"""
    student = db.students.get(student_id)
    if not student:
        return HTMLResponse(content="<h1>Error: Student not found</h1>", status_code=404)
    
    student_evals = []
    for ev in db.evaluations.values():
        ans = db.answers.get(ev.answer_id)
        if ans and ans.student_id == student_id:
            student_evals.append(ev)
    
    if not student_evals:
        return HTMLResponse(content="<h1>Error: No evaluations found for this student</h1>", status_code=404)
    
    questions_by_id = {q.id: q for q in db.questions.values()}
    
    html = render_student_report_html_enhanced(student, student_evals, questions_by_id)
    
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-cache",
            "Content-Type": "text/html; charset=utf-8"
        }
    )


@router.get("/summary/csv")
async def export_summary_csv():
    """Export all evaluations as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Student Name",
        "Roll Number",
        "Question Number",
        "Question Text",
        "Score",
        "Max Score",
        "Percentage",
        "Feedback"
    ])
    
    # Data
    for ev in db.evaluations.values():
        ans = db.answers.get(ev.answer_id)
        if not ans:
            continue
        
        student = db.students.get(ans.student_id)
        q = db.questions.get(ev.question_id)
        
        percentage = round((ev.score / ev.max_score * 100) if ev.max_score > 0 else 0, 2)
        
        writer.writerow([
            student.name if student else "Unknown",
            student.roll_no if student else "Unknown",
            q.question_number if q else "?",
            (q.text[:50] + "...") if q and len(q.text) > 50 else (q.text if q else ""),
            ev.score,
            ev.max_score,
            percentage,
            ev.feedback[:100] + "..." if len(ev.feedback) > 100 else ev.feedback
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=evaluation_summary.csv"}
    )


@router.get("/summary/json")
async def export_summary_json():
    """Export all evaluations as JSON with full details"""
    result = []
    
    for student in db.students.values():
        student_evals = []
        total_score = 0.0
        total_max = 0.0
        
        for ev in db.evaluations.values():
            ans = db.answers.get(ev.answer_id)
            if ans and ans.student_id == student.id:
                q = db.questions.get(ev.question_id)
                student_evals.append({
                    "question_number": q.question_number if q else "?",
                    "question_text": q.text if q else "Unknown",
                    "student_answer": ans.text,
                    "score": ev.score,
                    "max_score": ev.max_score,
                    "feedback": ev.feedback,
                    "rubric_breakdown": ev.rubric_breakdown,
                    "model_comparison": ev.model_answer_comparison,
                    "syllabus_topics": ev.syllabus_topic_ids,
                    "textbook_refs": ev.textbook_refs
                })
                total_score += ev.score
                total_max += ev.max_score
        
        if student_evals:
            result.append({
                "student_name": student.name,
                "student_roll": student.roll_no,
                "total_score": round(total_score, 2),
                "total_max": round(total_max, 2),
                "percentage": round((total_score / total_max * 100) if total_max > 0 else 0, 2),
                "evaluations": student_evals
            })
    
    return {"students": result, "total_students": len(result)}


@router.get("/dashboard")
async def get_dashboard_data():
    """Get summary data for dashboard"""
    total_students = len(db.students)
    total_questions = len(db.questions)
    total_answers = len(db.answers)
    total_evaluations = len(db.evaluations)
    
    # Calculate statistics
    scores = []
    for ev in db.evaluations.values():
        if ev.max_score > 0:
            percentage = (ev.score / ev.max_score) * 100
            scores.append(percentage)
    
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # Student-wise summary
    student_summary = []
    for student in db.students.values():
        student_total = 0.0
        student_max = 0.0
        question_count = 0
        
        for ev in db.evaluations.values():
            ans = db.answers.get(ev.answer_id)
            if ans and ans.student_id == student.id:
                student_total += ev.score
                student_max += ev.max_score
                question_count += 1
        
        if question_count > 0:
            percentage = (student_total / student_max * 100) if student_max > 0 else 0
            student_summary.append({
                "student_id": student.id,
                "name": student.name,
                "roll_no": student.roll_no,
                "total_score": round(student_total, 2),
                "total_max": round(student_max, 2),
                "percentage": round(percentage, 2),
                "questions_answered": question_count
            })
    
    # Sort by percentage descending
    student_summary.sort(key=lambda x: x["percentage"], reverse=True)
    
    return {
        "statistics": {
            "total_students": total_students,
            "total_questions": total_questions,
            "total_answers": total_answers,
            "total_evaluations": total_evaluations,
            "average_score_percentage": round(avg_score, 2)
        },
        "student_summary": student_summary
    }


def render_student_report_html_enhanced(
    student: Student,
    evals: List[Evaluation],
    questions_by_id: dict,
) -> str:
    """Enhanced HTML report with detailed evaluation"""
    import html
    
    rows = []
    total_score = 0.0
    total_max = 0.0
    
    for ev in evals:
        q = questions_by_id.get(ev.question_id)
        if not q:
            continue
        
        ans = db.answers.get(ev.answer_id)
        
        total_score += ev.score
        total_max += ev.max_score
        
        percentage = (ev.score / ev.max_score * 100) if ev.max_score > 0 else 0
        
        # Build rubric breakdown display
        rubric_html = ""
        if ev.rubric_breakdown:
            rubric_items = []
            for criterion, details in ev.rubric_breakdown.items():
                if isinstance(details, dict):
                    awarded = details.get('awarded', 0)
                    max_weight = details.get('max_weight', 0)
                    rubric_items.append(f"{html.escape(str(criterion))}: {awarded}/{max_weight}")
                else:
                    rubric_items.append(f"{html.escape(str(criterion))}: {html.escape(str(details))}")
            
            if rubric_items:
                rubric_html = "<div style='margin-top: 8px;'><strong style='font-size: 10px;'>Rubric Breakdown:</strong></div>"
                for item in rubric_items:
                    rubric_html += f"<div class='rubric-item'>• {item}</div>"
        
        # Escape all text content to prevent HTML/PDF corruption
        q_text = html.escape(q.text[:150] + '...' if len(q.text) > 150 else q.text)
        ans_text = html.escape(ans.text[:200] + '...' if ans and len(ans.text) > 200 else (ans.text if ans else ''))
        feedback = html.escape(ev.feedback[:300] + '...' if len(ev.feedback) > 300 else ev.feedback)
        model_comp = html.escape(ev.model_answer_comparison[:120] + '...') if ev.model_answer_comparison and len(ev.model_answer_comparison) > 120 else (html.escape(ev.model_answer_comparison) if ev.model_answer_comparison else '')
        
        rows.append(f"""
            <tr>
                <td style='text-align: center; font-weight: 600;'>{q.question_number}</td>
                <td>{q_text}</td>
                <td style='font-style: italic; color: #4b5563;'>{ans_text}</td>
                <td style='text-align: center; font-weight: 600;'>{ev.score:.1f} / {ev.max_score:.1f}<br><span style='font-size: 10px; color: #6b7280;'>({percentage:.0f}%)</span></td>
                <td>
                    <div style='margin-bottom: 5px;'><strong style='font-size: 10px;'>Feedback:</strong></div>
                    <div style='font-size: 10px; color: #374151;'>{feedback}</div>
                    {rubric_html}
                    {('<div style="margin-top: 8px;"><strong style="font-size: 10px;">Model Comparison:</strong><br><span style="font-size: 10px; color: #6b7280;">' + model_comp + '</span></div>') if model_comp else ''}
                </td>
            </tr>
        """)
    
    overall_percent = (total_score / total_max * 100) if total_max else 0.0
    
    # Determine grade
    if overall_percent >= 90:
        grade = "A+"
        grade_color = "#2ecc71"
    elif overall_percent >= 80:
        grade = "A"
        grade_color = "#27ae60"
    elif overall_percent >= 70:
        grade = "B"
        grade_color = "#f39c12"
    elif overall_percent >= 60:
        grade = "C"
        grade_color = "#e67e22"
    elif overall_percent >= 50:
        grade = "D"
        grade_color = "#e74c3c"
    else:
        grade = "F"
        grade_color = "#c0392b"
    
    rows_html = "\n".join(rows)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        @page {{
            margin: 2cm;
        }}
        body {{ 
            font-family: 'Georgia', serif; 
            margin: 0;
            padding: 20px;
            font-size: 12px;
            color: #1f2937;
            line-height: 1.5;
        }}
        .header {{
            border-bottom: 3px solid #1f2937;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
            color: #1f2937;
            letter-spacing: -0.5px;
        }}
        .header .subtitle {{
            margin: 8px 0 0 0;
            font-size: 14px;
            color: #6b7280;
            font-weight: normal;
        }}
        .info-section {{
            margin-bottom: 25px;
            background: #f9fafb;
            padding: 15px;
            border-left: 4px solid #1f2937;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        .info-row:last-child {{
            margin-bottom: 0;
        }}
        .info-label {{
            font-weight: 600;
            color: #374151;
            min-width: 120px;
        }}
        .info-value {{
            color: #1f2937;
            font-weight: 500;
        }}
        .summary-box {{
            background: #f3f4f6;
            border: 2px solid #d1d5db;
            padding: 12px 15px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .summary-box .score {{
            font-size: 22px;
            font-weight: 700;
            color: #1f2937;
            margin-bottom: 5px;
        }}
        .summary-box .grade {{
            display: inline-block;
            background: {grade_color};
            color: white;
            padding: 8px 20px;
            font-size: 20px;
            font-weight: 700;
            border-radius: 4px;
            margin-top: 5px;
        }}
        h2 {{
            font-size: 16px;
            font-weight: 600;
            color: #1f2937;
            margin: 25px 0 12px 0;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 5px;
        }}
        table {{ 
            width: 100%; 
            border-collapse: collapse;
            margin-top: 10px;
            background: white;
        }}
        th, td {{ 
            border: 1px solid #d1d5db; 
            padding: 10px;
            font-size: 11px;
            vertical-align: top;
            text-align: left;
        }}
        th {{ 
            background: #f3f4f6;
            color: #1f2937;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background: #f9fafb;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #d1d5db;
            text-align: center;
            font-size: 10px;
            color: #9ca3af;
        }}
        .rubric-item {{
            margin: 3px 0;
            font-size: 10px;
            color: #4b5563;
        }}
      </style>
    </head>
    <body>
      <div class="header">
        <h1>Examination Evaluation Report</h1>
        <div class="subtitle">Engineering Thermodynamics</div>
      </div>
      
      <div class="info-section">
        <div class="info-row">
            <span class="info-label">Student Name:</span>
            <span class="info-value">{html.escape(student.name)}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Roll Number:</span>
            <span class="info-value">{html.escape(student.roll_no)}</span>
        </div>
        <div class="info-row">
            <span class="info-label">Questions Answered:</span>
            <span class="info-value">{len(evals)}</span>
        </div>
      </div>
      
      <div class="summary-box">
        <div class="score">
            Total Score: {total_score:.1f} / {total_max:.1f} ({overall_percent:.1f}%)
        </div>
        <div class="grade">{grade}</div>
      </div>
      
      <h2>Detailed Question-wise Evaluation</h2>
      
      <table>
        <thead>
          <tr>
            <th style="width: 5%;">Q#</th>
            <th style="width: 25%;">Question</th>
            <th style="width: 30%;">Your Answer</th>
            <th style="width: 10%;">Score</th>
            <th style="width: 30%;">Evaluation</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
      
      <div class="footer">
        <p>Answer Evaluator System</p>
      </div>
    </body>
    </html>
    """
    return html
