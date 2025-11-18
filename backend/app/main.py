from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes.routes_ingest import router as ingest_router
from .api.routes.routes_rubric import router as rubric_router
from .api.routes.routes_evaluate import router as evaluate_router
from .api.routes.routes_questions import router as questions_router
from .api.routes.routes_answer import router as answer_router
from .api.routes.routes_reports import router as reports_router
from .services.startup_loader import load_reference_textbook_if_needed

app = FastAPI(
    title="Answer Evaluator",
    description="AI-powered exam answer evaluation system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(ingest_router)
app.include_router(rubric_router)
app.include_router(evaluate_router)
app.include_router(questions_router)
app.include_router(answer_router)
app.include_router(reports_router)

@app.on_event("startup")
async def startup_event():
    # pre-load reference book from disk into memory + vectorstore
    load_reference_textbook_if_needed()

@app.get("/")
async def root():
    return {"message": "Answer Evaluator backend is running"}
