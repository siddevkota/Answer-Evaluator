# 🎓 Answer Evaluator


An AI-powered exam answer evaluation system built with FastAPI and Streamlit.An AI-powered system for evaluating student exam answers using OpenAI's GPT models. The system can automatically generate rubrics, evaluate answers against syllabus topics and textbooks, and provide detailed feedback.



## 📋 Table of Contents

- [Features](#features)

- [Project Structure](#project-structure)- **PDF Ingestion**: Upload syllabus, textbooks, and question papers

- [Requirements](#requirements)- **Automatic Rubric Generation**: AI-powered rubric creation based on questions

- [Installation](#installation)- **Manual Rubric Mode**: Define custom rubrics for each question

- [Usage](#usage)- **Answer Evaluation**: Automated grading with detailed feedback

- [API Documentation](#api-documentation)- **Vector Search**: Contextual retrieval from syllabus and textbooks

- **REST API**: FastAPI backend for all operations

## ✨ Features

- **Web UI**: Streamlit frontend for easy interaction

- **Question Management**: Load questions from PDF or JSON files## Prerequisites

- **Answer Upload**: Submit student answers in PDF or JSON format

- **AI Evaluation**: Automatic grading using GPT-4 with rubric-based assessment- Python 3.12+

- **Model Answer Comparison**: Compare student answers against model answers- OpenAI API key

- **Comprehensive Reports**: Generate HTML, PDF, CSV, and JSON reports

- **Interactive Dashboard**: View performance metrics and statistics## Setup Instructions

- **Rubric System**: Manual or automatic rubric generation

### 1. Install Dependencies

## 📁 Project Structure

Dependencies are already installed in the virtual environment. If you need to reinstall:

```

answer-evaluator/```bash

├── backend/                    # FastAPI backendsource .venv/bin/activate  # On macOS/Linux

│   └── app/pip install -r requirements.txt

│       ├── api/               # API layer```

│       │   └── routes/        # API route handlers

│       ├── core/              # Core (config, models, db)### 2. Configure Environment Variables

│       ├── services/          # Business services (LLM, vectorstore)

│       ├── utils/             # Utilities (PDF, reports)Edit the `.env` file and add your OpenAI API key:

│       └── main.py            # Application entry point

├── frontend/                  # Streamlit UI```bash

│   └── app.pyOPENAI_API_KEY=your_actual_api_key_here

├── data/                      # Data filesOPENAI_MODEL=gpt-4-turbo-preview

├── scripts/                   # Helper scripts```

└── .env                       # Environment variables

```
### 3. Run the Application


## 🔧 RequirementsYou have two options:



- **Python**: 3.14.0 (Homebrew)#### Option A: Run Backend and Frontend in Separate Terminals

- **System Libraries**: Pango, Cairo (for PDF generation)

- **API Key**: OpenAI API key**Terminal 1 - Backend:**

```bash

### Install System Dependencies (macOS)./run_backend.sh

```

```bashThe backend will start at http://localhost:8000

brew install python@3.14 pango libffi cairo gdk-pixbuf

```**Terminal 2 - Frontend:**

```bash

## 🚀 Installation./run_frontend.sh

```

### 1. Create Virtual Environment (Must use Homebrew Python!)The frontend will start at http://localhost:8501



```bash#### Option B: Manual Commands

/Users/ebpearls1/homebrew/opt/python@3.14/bin/python3.14 -m venv .venv

source .venv/bin/activate**Backend:**

``````bash

source .venv/bin/activate

### 2. Install Dependenciesexport $(cat .env | grep -v '^#' | xargs)

uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

```bash```

pip install -r requirements.txt

```**Frontend:**

```bash

### 3. Configure Environmentsource .venv/bin/activate

export $(cat .env | grep -v '^#' | xargs)

```bashstreamlit run frontend/app.py

cp .env.example .env```

# Edit .env and add: OPENAI_API_KEY=sk-your-key-here

```## Project Structure



## 🎯 Usage```

test_project/

### Start Backend├── backend/

│   └── app/

```bash│       ├── __init__.py

bash scripts/run_backend.sh│       ├── config.py          # Configuration and environment variables

# Or manually: uvicorn backend.app.main:app --reload --port 8000│       ├── db.py              # In-memory database models

```│       ├── llm.py             # OpenAI LLM integration

│       ├── main.py            # FastAPI application entry point

Backend: http://localhost:8000│       ├── models.py          # Pydantic models

│       ├── pdf_utils.py       # PDF text extraction utilities

### Start Frontend│       ├── report.py          # Report generation

│       ├── routes_evaluate.py # Evaluation endpoints

```bash│       ├── routes_ingest.py   # Document ingestion endpoints

bash scripts/run_frontend.sh  │       ├── routes_rubric.py   # Rubric management endpoints

# Or manually: streamlit run frontend/app.py --server.port 8501│       └── vectorstore.py     # Vector storage for semantic search

```├── frontend/

│   └── app.py                 # Streamlit web interface

Frontend: http://localhost:8501├── .env                       # Environment variables (create from .env.example)

├── .env.example               # Example environment configuration

## 📚 API Documentation├── requirements.txt           # Python dependencies

├── run_backend.sh            # Script to run backend

- **Swagger UI**: http://localhost:8000/docs├── run_frontend.sh           # Script to run frontend

- **ReDoc**: http://localhost:8000/redoc└── README.md                 # This file

```

### Key Endpoints

## Usage Workflow

- `POST /questions/load-from-pdf` - Load questions

- `POST /answer/upload-pdf` - Upload student answer1. **Upload Syllabus**: Upload a PDF containing the course syllabus

- `POST /evaluate/run/{exam_id}` - Run evaluation2. **Upload Textbook**: Upload textbook PDF(s) for reference material

- `GET /reports/student/{id}/html` - Generate report3. **Upload Question Paper**: Upload the exam question paper

- `GET /reports/dashboard` - View statistics4. **Configure Rubrics**: 

   - **Auto mode**: AI generates rubrics automatically

## 🐛 Troubleshooting   - **Manual mode**: Define custom rubrics in JSON format

5. **Run Evaluation**: Process and evaluate student answers

### WeasyPrint OSError6. **View Reports**: (Feature in development)

Ensure you're using Homebrew Python (not system Python):

```bash## API Endpoints

which python  # Should show .venv/bin/python

weasyprint --version  # Should work without errors### Ingestion

```- `POST /ingest/syllabus` - Upload and process syllabus PDF

- `POST /ingest/textbook` - Upload and process textbook PDF

### Dashboard TypedDict Error- `POST /ingest/exam` - Upload and process exam questions

Downgrade pandas if using Python 3.14:

```bash### Rubric Management

pip install 'pandas<2.3,>=2.0'- `POST /rubric/manual/{question_id}` - Set manual rubric for a question

```

### Evaluation

## 📝 License- `POST /evaluate/run/{exam_id}` - Run evaluation for all answers



MIT License### Health Check

- `GET /` - Check if backend is running

## Development Notes

- The system uses in-memory storage (no database required for now)
- Vector stores are created in-memory using numpy for similarity search
- All PDFs are processed using pypdf library
- OpenAI GPT-4 is used for rubric generation and answer evaluation

## Troubleshooting

### "OPENAI_API_KEY is not set" warning
Make sure you've:
1. Created a `.env` file from `.env.example`
2. Added your actual OpenAI API key
3. Restarted the backend server

### Import errors
Ensure you've activated the virtual environment and installed all dependencies:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Port already in use
If port 8000 or 8501 is already in use, you can modify the port in the run scripts or manual commands.

## Future Enhancements

- Student answer upload functionality
- PDF report generation
- Per-student dashboards
- Database persistence (PostgreSQL/SQLite)
- Authentication and user management
- Batch processing of multiple exams
- Enhanced analytics and visualizations
