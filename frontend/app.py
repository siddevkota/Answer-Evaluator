import json
import streamlit as st
import httpx
import pandas as pd
from io import BytesIO

BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Answer Evaluator", layout="wide")

# Simple, clean CSS
st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
    }
    h1 {
        color: #1f2937;
        font-weight: 600;
    }
    h2 {
        color: #374151;
        font-weight: 500;
        margin-top: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

st.title("Answer Evaluator System")

# Sidebar
with st.sidebar:
    st.subheader("Configuration")
    rubric_mode = st.radio(
        "Rubric Mode",
        options=["auto", "manual"],
        format_func=lambda x: "Automatic" if x == "auto" else "Manual"
    )
    st.divider()
    st.caption("Reference textbook loaded at startup")

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Setup", 
    "Questions & Answers", 
    "Evaluation", 
    "Dashboard",
    "Reports"
])

# ====================
# TAB 1: SETUP
# ====================
with tab1:
    st.subheader("Initial Setup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Upload Syllabus")
        syllabus_file = st.file_uploader("Upload Syllabus PDF", type=["pdf"], key="syllabus")
        if st.button("Ingest Syllabus", width='stretch'):
            if syllabus_file:
                with st.spinner("Processing syllabus..."):
                    files = {"file": (syllabus_file.name, syllabus_file.getvalue(), syllabus_file.type)}
                    try:
                        with httpx.Client(timeout=60.0) as client:
                            resp = client.post(f"{BACKEND_URL}/ingest/syllabus", files=files)
                        st.success(f"{resp.json()}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Please upload a file first")
    
    with col2:
        st.markdown("##### Load Questions")
        exam_id = st.number_input("Exam ID", min_value=1, value=1, key="exam_id_setup")
        if st.button("Load Questions from QA_generated.pdf", width='stretch'):
            with st.spinner("Loading questions from QA data..."):
                try:
                    with httpx.Client(timeout=60.0) as client:
                        resp = client.post(
                            f"{BACKEND_URL}/questions/load-from-qa",
                            params={"exam_id": exam_id}
                        )
                    result = resp.json()
                    st.success(f"Loaded {result.get('questions_loaded', 0)} questions from {result.get('chapters_processed', 0)} chapters")
                    st.session_state["exam_id"] = exam_id
                    
                    # Get and display rubrics
                    with httpx.Client(timeout=10.0) as client:
                        q_resp = client.get(f"{BACKEND_URL}/questions/list")
                    questions = q_resp.json().get("questions", [])
                    if questions:
                        st.session_state["questions_with_rubrics"] = questions
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.divider()
    
    # System Status
    st.markdown("##### System Status")
    if st.button("Refresh Status"):
        try:
            with httpx.Client(timeout=10.0) as client:
                q_resp = client.get(f"{BACKEND_URL}/questions/list")
                a_resp = client.get(f"{BACKEND_URL}/answer/list")
                
                q_data = q_resp.json()
                a_data = a_resp.json()
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Questions", q_data.get("total", 0))
                col2.metric("Answers", a_data.get("total", 0))
                col3.metric("Ready", "Yes" if q_data.get("total", 0) > 0 else "No")
        except:
            st.error("Backend not responding")
    
    # Display Rubrics if questions loaded
    if "questions_with_rubrics" in st.session_state:
        st.divider()
        st.markdown("##### AI-Generated Rubrics")
        questions = st.session_state["questions_with_rubrics"]
        
        for q in questions:
            with st.expander(f"Q{q['question_number']}: {q['text'][:80]}..."):
                if q.get('model_answer'):
                    st.markdown(f"**Model Answer:** {q['model_answer'][:200]}...")
                
                if q.get('rubric'):
                    st.markdown("**Grading Rubric:**")
                    rubric = q['rubric']
                    
                    for i, crit in enumerate(rubric.get('criteria', []), 1):
                        st.markdown(f"**{i}. {crit['criterion']}** ({crit['weight']} marks)")
                        st.caption(crit['description'])
                else:
                    st.info("Rubric will be generated automatically during evaluation")

# ====================
# TAB 2: QUESTIONS & ANSWERS
# ====================
with tab2:
    st.subheader("Questions & Student Answers")
    
    # View Questions
    with st.expander("View Loaded Questions", expanded=False):
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{BACKEND_URL}/questions/list")
            questions = resp.json().get("questions", [])
            
            if questions:
                df = pd.DataFrame(questions)
                st.dataframe(df, width='stretch', height=300)
            else:
                st.info("No questions loaded. Load questions from the Setup tab.")
        except Exception as e:
            st.error(f"Error loading questions: {str(e)}")
    
    st.divider()
    
    # Upload Student Answers
    st.markdown("##### Upload Student Answers")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        answer_file = st.file_uploader(
            "Upload Student Answer File (PDF or JSON)", 
            type=["pdf", "json"]
        )
    
    with col2:
        st.caption("JSON Format Example:")
        st.code('''
{
  "student_name": "John Doe",
  "student_roll": "S12345",
  "answers": [
    {
      "question_number": "1",
      "answer_text": "..."
    }
  ]
}
        ''', language="json")
    
    if st.button("Upload Answers", type="primary", width='stretch'):
        if answer_file:
            with st.spinner("Processing student answers..."):
                try:
                    files = {"file": (answer_file.name, answer_file.getvalue(), answer_file.type or "application/pdf")}
                    with httpx.Client(timeout=90.0) as client:
                        resp = client.post(f"{BACKEND_URL}/answer/upload", files=files)
                    result = resp.json()
                    st.success(f"Uploaded answers for {result.get('student_name')} (Roll: {result.get('student_roll')})")
                    st.info(f"Answers added: {result.get('answers_added', 0)}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please upload a file first")
    
    # View Uploaded Answers
    with st.expander("View Uploaded Answers", expanded=False):
        if st.button("Refresh Answers List"):
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(f"{BACKEND_URL}/answer/list")
                answers = resp.json().get("answers", [])
                
                if answers:
                    df = pd.DataFrame(answers)
                    st.dataframe(df, width='stretch', height=300)
                    
                    # Clear answers button
                    if st.button("Clear All Answers"):
                        with httpx.Client(timeout=10.0) as client:
                            client.delete(f"{BACKEND_URL}/answer/clear")
                        st.success("All answers cleared")
                        st.rerun()
                else:
                    st.info("No answers uploaded yet")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ====================
# TAB 3: EVALUATION
# ====================
with tab3:
    st.subheader("Run Evaluation")
    
    exam_id = st.session_state.get("exam_id", 1)
    st.write(f"**Exam ID:** {exam_id}")
    st.write(f"**Rubric Mode:** {'Automatic' if rubric_mode == 'auto' else 'Manual'}")
    
    st.divider()
    
    if st.button("Run Complete Evaluation", type="primary", width='stretch'):
        with st.spinner("Evaluating all answers... This may take a few minutes..."):
            try:
                with httpx.Client(timeout=300.0) as client:  # 5 minutes timeout
                    resp = client.post(f"{BACKEND_URL}/evaluate/run/{exam_id}")
                result = resp.json()
                
                st.success("Evaluation Complete!")
                st.info(f"Evaluations Created: {result.get('evaluations_created', 0)}")
                st.info(f"Rubric Mode Used: {result.get('rubric_mode', 'unknown')}")
                
            except Exception as e:
                st.error(f"Evaluation failed: {str(e)}")
    
    st.divider()
    
    # View Evaluation Results with Rubric Details
    with st.expander("View Evaluation Results", expanded=True):
        if st.button("Refresh Evaluations"):
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(f"{BACKEND_URL}/evaluate/list")
                evals = resp.json().get("evaluations", [])
                
                if evals:
                    for eval_item in evals:
                        with st.container():
                            st.markdown(f"**Student:** {eval_item.get('student_name')} | **Q{eval_item.get('q_number')}** | **Score:** {eval_item.get('score')}/{eval_item.get('max_score')}")
                            
                            # Show rubric breakdown if available
                            if eval_item.get('rubric_breakdown'):
                                st.caption("Rubric Breakdown:")
                                breakdown = eval_item['rubric_breakdown']
                                for criterion, details in breakdown.items():
                                    st.markdown(f"- {criterion}: {details.get('awarded', 0)}/{details.get('max_weight', 0)} marks - {details.get('justification', '')}")
                            
                            st.caption(f"Feedback: {eval_item.get('feedback', '')[:200]}...")
                            st.divider()
                else:
                    st.info("No evaluations yet. Run evaluation first.")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ====================
# TAB 4: DASHBOARD
# ====================
with tab4:
    st.subheader("Evaluation Dashboard")
    
    if st.button("Refresh Dashboard", width='stretch'):
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{BACKEND_URL}/reports/dashboard")
            data = resp.json()
            
            # Statistics
            stats = data.get("statistics", {})
            col1, col2, col3, col4, col5 = st.columns(5)
            
            col1.metric("Students", stats.get("total_students", 0))
            col2.metric("Questions", stats.get("total_questions", 0))
            col3.metric("Answers", stats.get("total_answers", 0))
            col4.metric("Evaluations", stats.get("total_evaluations", 0))
            col5.metric("Avg Score", f"{stats.get('average_score_percentage', 0):.1f}%")
            
            st.divider()
            
            # Student Summary
            st.markdown("##### Student Performance")
            students = data.get("student_summary", [])
            
            if students:
                df = pd.DataFrame(students)
                st.dataframe(df, width='stretch', height=400)
                
                # Chart
                st.markdown("##### Score Distribution")
                names = [s['name'] for s in students]
                percentages = [s['percentage'] for s in students]
                chart_df = pd.DataFrame({'percentage': percentages}, index=names)
                st.bar_chart(chart_df)
                
            else:
                st.info("No student data available yet")
                
        except Exception as e:
            import traceback
            st.error(f"Error loading dashboard: {str(e)}")
            st.code(traceback.format_exc())

# ====================
# TAB 5: REPORTS
# ====================
with tab5:
    st.subheader("Generate Reports")
    
    # Get student list
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{BACKEND_URL}/reports/dashboard")
        students = resp.json().get("student_summary", [])
    except:
        students = []
    
    if students:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Individual Student Reports")
            selected_student = st.selectbox(
                "Select Student",
                options=students,
                format_func=lambda x: f"{x['name']} ({x['roll_no']}) - {x['percentage']:.1f}%"
            )
            
            if selected_student:
                student_id = selected_student['student_id']
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    if st.button("Generate PDF", width='stretch'):
                        with st.spinner("Generating PDF..."):
                            try:
                                with httpx.Client(timeout=30.0) as client:
                                    resp = client.get(f"{BACKEND_URL}/reports/student/{student_id}/pdf")
                                
                                if resp.status_code == 200:
                                    st.download_button(
                                        label="Download PDF",
                                        data=resp.content,
                                        file_name=f"report_{selected_student['roll_no']}.pdf",
                                        mime="application/pdf",
                                        width='stretch'
                                    )
                                else:
                                    st.error("Failed to generate PDF")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                
                with col_b:
                    html_url = f"{BACKEND_URL}/reports/student/{student_id}/html"
                    st.link_button(
                        "View HTML Report",
                        html_url,
                        width='stretch'
                    )
        
        with col2:
            st.markdown("##### Export All Results")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("Download CSV", width='stretch'):
                    try:
                        with httpx.Client(timeout=30.0) as client:
                            resp = client.get(f"{BACKEND_URL}/reports/summary/csv")
                        
                        if resp.status_code == 200:
                            st.download_button(
                                label="Download CSV File",
                                data=resp.content,
                                file_name="evaluation_summary.csv",
                                mime="text/csv",
                                width='stretch'
                            )
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            
            with col_b:
                if st.button("Download JSON", width='stretch'):
                    try:
                        with httpx.Client(timeout=30.0) as client:
                            resp = client.get(f"{BACKEND_URL}/reports/summary/json")
                        
                        if resp.status_code == 200:
                            st.download_button(
                                label="Download JSON File",
                                data=json.dumps(resp.json(), indent=2),
                                file_name="evaluation_export.json",
                                mime="application/json",
                                width='stretch'
                            )
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    else:
        st.info("No evaluations available yet. Complete the evaluation process first.")

# # Footer
# st.markdown("---")
# st.markdown("""
# <div style='text-align: center; color: #666; padding: 2rem 0;'>
#     <p>🤖 AI-Powered Answer Evaluator | Built with FastAPI & Streamlit</p>
#     <p style='font-size: 0.8rem;'>Evaluates student answers using OpenAI GPT-4 & semantic search</p>
# </div>
# """, unsafe_allow_html=True)
