# Answer Evaluator

AI-powered exam answer grading system using FastAPI (backend) and Streamlit (frontend).

## Features
- Upload syllabus, textbooks, and question papers (PDF/JSON)
- Automatic or manual rubric generation
- AI-based answer evaluation using OpenAI GPT
- Detailed feedback and report generation (HTML, PDF, CSV, JSON)
- Simple web dashboard for results

## How to Run
1. Copy `.env.example` to `.env` and add your OpenAI API key.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start backend:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```
4. Start frontend:
   ```bash
   streamlit run frontend/app.py
   ```

## Future Enhancements
- Student dashboards
- PDF report generation
- Database support
- Authentication
- Batch exam processing
- More analytics and visualizations
