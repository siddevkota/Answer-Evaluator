from typing import List
from weasyprint import HTML
from .models import Question, Evaluation, Student

def render_student_report_html(
    student: Student,
    evals: List[Evaluation],
    questions_by_id: dict,
) -> str:
    rows = []
    total_score = 0.0
    total_max = 0.0
    for ev in evals:
        q = questions_by_id.get(ev.answer_id and ev.answer_id)  # simplistic placeholder
        # In a real app, you'd map Evaluation -> Answer -> Question properly.
        qtext = getattr(q, "text", "Question text N/A")
        max_marks = getattr(q, "max_marks", 0.0)
        total_score += ev.score
        total_max += max_marks
        rows.append(
            f"<tr><td>{qtext}</td><td>{ev.score}/{max_marks}</td>"
            f"<td>{ev.feedback}</td></tr>"
        )
    percent = (total_score / total_max * 100) if total_max else 0.0
    rows_html = "\n".join(rows)
    html = f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        body {{ font-family: sans-serif; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ccc; padding: 4px; font-size: 12px; }}
        th {{ background: #eee; }}
      </style>
    </head>
    <body>
      <h1>Exam Report</h1>
      <h2>{student.name} (Roll: {student.roll_no})</h2>
      <p>Total: {total_score:.1f} / {total_max:.1f} ({percent:.1f}%)</p>
      <table>
        <thead>
          <tr><th>Question</th><th>Score</th><th>Feedback</th></tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </body>
    </html>
    """
    return html

def html_to_pdf_bytes(html: str) -> bytes:
    return HTML(string=html).write_pdf()
