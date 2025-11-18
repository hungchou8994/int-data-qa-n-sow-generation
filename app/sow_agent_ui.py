"""
Streamlit UI for SOW Generation with Agent-Based Quality Control
Implements:
- PHASE 1: Auto-correction loop (generate -> judge -> regenerate)
- PHASE 2: Human review with separate feedback for each component
- PHASE 3: Cascade regeneration based on feedback
- PHASE 4: Approval and export
"""

import streamlit as st
import json
import os
import sys
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from scope_of_work.model import (
        ClientInformation,
        QuestionnaireAnswer,
        ProjectDetail,
        ProjectAssumption,
        ScopeOfWork,
        GenerationConfig,
        JudgeResult
    )
    from scope_of_work.orchestrator import SOWOrchestrator, OrchestrationResult
    from scope_of_work.sheet_reader import read_questionnaire_from_google_sheet
    from sow_sheet.connect import SOWGoogleSheetsConnector
    from sow_sheet.model import SheetOperation
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.stop()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="SOW Generator - Agent System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.8rem;
        color: #2e8b57;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 3px solid #2e8b57;
        padding-bottom: 0.5rem;
    }
    .component-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.8rem;
        border-left: 5px solid #1f77b4;
        margin-bottom: 1.5rem;
    }
    .judge-pass {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin-bottom: 1rem;
    }
    .judge-fail {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc3545;
        margin-bottom: 1rem;
    }
    .sow-task-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1.5rem;
        border-left: 4px solid #1f77b4;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .sow-task-card h4 {
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sow-task-card p {
        line-height: 1.8;
        margin-bottom: 0.8rem;
    }
    .metric-card {
        background-color: #fff3cd;
        padding: 0.8rem;
        border-radius: 0.5rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables"""
    if 'orchestrator' not in st.session_state:
        st.session_state.orchestrator = None
    if 'client_info' not in st.session_state:
        st.session_state.client_info = None
    if 'questionnaire_answers' not in st.session_state:
        st.session_state.questionnaire_answers = []
    if 'result' not in st.session_state:
        st.session_state.result = None
    if 'workflow_stage' not in st.session_state:
        st.session_state.workflow_stage = "input"  # "input", "phase1", "phase2", "approved"


def render_sidebar():
    """Render sidebar configuration"""
    st.sidebar.title("⚙️ Configuration")
    
    # API Configuration
    st.sidebar.subheader("API Settings")
    default_api_key = os.getenv('GOOGLE_API_KEY', '')
    
    if default_api_key:
        st.sidebar.success("✅ API Key loaded from .env")
    else:
        st.sidebar.error("❌ API Key not found")
    
    # Generation Settings
    st.sidebar.subheader("Generation Settings")
    temperature = st.sidebar.slider("LLM Temperature", 0.0, 1.0, 0.7, 0.1)
    max_auto_retries = st.sidebar.slider("Max Auto-Retries (Judge Loop)", 1, 5, 3)
    
    # Judge Settings
    st.sidebar.subheader("Quality Control")
    pass_threshold = st.sidebar.slider("Judge Pass Threshold", 50, 100, 75, 5)
    st.sidebar.info(f"Components must score ≥ {pass_threshold}/100 to pass")
    
    # RAG Settings
    st.sidebar.subheader("RAG Settings (SoW)")
    top_k = st.sidebar.slider("Top K Similar Tasks", 0, 30, 10, 5)
    st.sidebar.info(f"Retrieve {top_k} most similar tasks from past projects")
    
    return {
        'temperature': temperature,
        'max_auto_retries': max_auto_retries,
        'pass_threshold': pass_threshold,
        'top_k': top_k
    }


def render_client_info_form():
    """Render client information input form"""
    st.markdown('<h2 class="section-header">👤 Client Information</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        customer_name = st.text_input("Customer Name *", placeholder="e.g., ABC Technology")
        business_domain = st.selectbox(
            "Business Domain *",
            ["IT and Software Services", "Healthcare", "Finance and Banking", 
             "E-commerce", "Manufacturing", "Education", "Real Estate", 
             "Consulting", "Other"]
        )
        requirements = st.text_area(
            "Project Requirements *",
            placeholder="Describe the project requirements...",
            height=100
        )
        audience = st.text_input("Target Audience *", placeholder="e.g., IT Team")
    
    with col2:
        project_type = st.selectbox(
            "Project Type",
            ["AI/ML Solution", "Data Analytics", "Automation System", 
             "Cloud Migration", "Web Application", "Mobile App", "Other"]
        )
        budget_range = st.selectbox(
            "Budget Range",
            ["Not specified", "$10K - $50K", "$50K - $100K", 
             "$100K - $500K", "$500K+"]
        )
        timeline = st.selectbox(
            "Timeline",
            ["Not specified", "1-3 months", "3-6 months", 
             "6-12 months", "12+ months"]
        )
        language = st.selectbox("Language", ["English", "Vietnamese"])
        additional_context = st.text_area(
            "Additional Context",
            placeholder="Any other relevant information...",
            height=100
        )
    
    return {
        'customer_name': customer_name,
        'business_domain': business_domain,
        'requirements': requirements,
        'audience': audience,
        'project_type': project_type if project_type != "Other" else None,
        'budget_range': budget_range if budget_range != "Not specified" else None,
        'timeline': timeline if timeline != "Not specified" else None,
        'language': language,
        'additional_context': additional_context if additional_context else None
    }


def render_questionnaire_answers_form():
    """Render questionnaire answers input form"""
    st.markdown('<h2 class="section-header">📝 Questionnaire Answers</h2>', unsafe_allow_html=True)
    
    input_method = st.radio(
        "Input Method",
        ["📊 Google Sheets", "✍️ Manual Entry"],
        horizontal=True
    )
    
    answers = []
    client_info_from_sheet = None
    
    if input_method == "📊 Google Sheets":
        sheet_url = st.text_input("Google Sheets URL", placeholder="https://docs.google.com/spreadsheets/d/...")
        worksheet_name = st.text_input("Worksheet Name", value="Sheet1")
        
        if st.button("📥 Load from Google Sheets"):
            if sheet_url and worksheet_name:
                with st.spinner("Loading from Google Sheets..."):
                    try:
                        data = read_questionnaire_from_google_sheet(sheet_url, worksheet_name)
                        answers = data['answers']
                        client_info_from_sheet = data['client_info']
                        st.session_state.loaded_answers = answers
                        st.session_state.loaded_client_info = client_info_from_sheet
                        st.success(f"✅ Loaded {len(answers)} answers from Google Sheets")
                        st.write("Client Information from Sheet:")
                        st.json(client_info_from_sheet)
                        st.write("Questionnaire Answers:")
                        for i, ans in enumerate(answers,start=1):
                            st.markdown("**Section: " + ans['section'] + "**")
                            st.markdown(f"**Q{i}**: {ans['question_text']}")
                            st.markdown(f"- Answer: {ans['answer']}")
                            st.markdown("---")
                    except Exception as e:
                        st.error(f"Error loading from Google Sheets: {str(e)}")
        
        # Use loaded data if available
        if 'loaded_answers' in st.session_state:
            answers = st.session_state.loaded_answers
            client_info_from_sheet = st.session_state.get('loaded_client_info')
    
    
    else:
        num_answers = st.number_input("Number of answers", min_value=1, max_value=50, value=5)
        answers = []
        for i in range(num_answers):
            with st.expander(f"Question {i+1}"):
                q_id = st.text_input(f"Question ID", value=f"Q{i+1}", key=f"qid_{i}")
                section = st.text_input(f"Section", value="General", key=f"sec_{i}")
                question = st.text_area(f"Question", key=f"q_{i}")
                answer = st.text_area(f"Answer", key=f"a_{i}")
                if question and answer:
                    answers.append({
                        'question_id': q_id,
                        'section': section,
                        'question_text': question,
                        'answer': answer
                    })
    
    return answers, client_info_from_sheet


def render_judge_result(judge_result: JudgeResult, component_name: str):
    """Render judge evaluation result"""
    if judge_result.status == "PASS":
        st.markdown(f'<div class="judge-pass">', unsafe_allow_html=True)
        st.markdown(f"### ✅ {component_name} - PASSED")
        st.markdown(f"**Score:** {judge_result.score}/100")
        st.markdown(f"**Feedback:** {judge_result.feedback}")
        if judge_result.issues:
            st.markdown("**Minor Issues:**")
            for issue in judge_result.issues:
                st.markdown(f"- {issue}")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="judge-fail">', unsafe_allow_html=True)
        st.markdown(f"### ❌ {component_name} - FAILED")
        st.markdown(f"**Score:** {judge_result.score}/100")
        st.markdown(f"**Feedback:** {judge_result.feedback}")
        if judge_result.issues:
            st.markdown("**Issues Found:**")
            for issue in judge_result.issues:
                st.markdown(f"- {issue}")
        st.markdown('</div>', unsafe_allow_html=True)


def render_project_detail(detail: ProjectDetail, judge_result: Optional[JudgeResult] = None):
    """Render Project Detail component"""
    st.markdown('<div class="component-card">', unsafe_allow_html=True)
    st.markdown("## 📋 Project Detail")
    
    # Metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Customer", detail.customer_name)
    with col2:
        st.metric("Domain", detail.business_domain)
    with col3:
        st.metric("Features", len(detail.key_features))
    
    # Overview
    st.markdown("### 📖 Overview")
    st.write(detail.overview)
    
    # Key Features
    st.markdown("### ⚡ Key Features")
    for feature in detail.key_features:
        st.markdown(feature)
        st.markdown("---")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Judge result
    if judge_result:
        render_judge_result(judge_result, "Project Detail")


def render_project_assumption(assumption: ProjectAssumption, judge_result: Optional[JudgeResult] = None):
    """Render Project Assumption component"""
    st.markdown('<div class="component-card">', unsafe_allow_html=True)
    st.markdown("## 📊 Project Assumptions")
    
    # Metadata
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Customer", assumption.customer_name)
    with col2:
        st.metric("Sections", len(assumption.assumptions))
    
    # Assumptions by section
    for section in assumption.assumptions:
        st.markdown(f"### {section.section}")
        for point in section.points:
            st.markdown(f"- {point}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Judge result
    if judge_result:
        render_judge_result(judge_result, "Project Assumption")


def render_scope_of_work(sow: ScopeOfWork, judge_result: Optional[JudgeResult] = None):
    """Render Scope of Work component"""
    st.markdown('<div class="component-card">', unsafe_allow_html=True)
    st.markdown("## 📝 Scope of Work")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Tasks", sow.total_tasks)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Man-Days", f"{sow.total_man_days:.1f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        rag_count = sum(1 for t in sow.tasks if t.source == "rag")
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("RAG Tasks", rag_count)
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        gen_count = sum(1 for t in sow.tasks if t.source == "generated")
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Generated Tasks", gen_count)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Tasks by category
    st.markdown("### 📋 Task Breakdown")
    grouped = sow.get_tasks_by_category()
    
    for category, tasks in grouped.items():
        with st.expander(f"**{category}** ({len(tasks)} tasks, {sum(t.man_days for t in tasks):.1f} days)"):
            for i, task in enumerate(tasks, 1):
                st.markdown(f'<div class="sow-task-card">', unsafe_allow_html=True)
                
                # Task header with number and man-days
                st.markdown(f"#### {i}. {task.task_title}")
                st.markdown(f"**⏱️ Duration:** {task.man_days} days")
                st.markdown(f"**📌 Source:** {task.source.upper()}")
                
                # Task content with proper line breaks
                st.markdown("**📝 Description:**")
                # Replace \n\n with actual line breaks for rendering
                formatted_content = task.content.replace("\\n\\n", "\n\n")
                st.markdown(formatted_content)
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Judge result
    if judge_result:
        render_judge_result(judge_result, "Scope of Work")


def main():
    """Main application"""
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">🤖 SOW Generator - Agent System</h1>', unsafe_allow_html=True)
    st.markdown("**AI-Powered SOW Generation with Automated Quality Control**")
    
    # Sidebar
    config_dict = render_sidebar()
    
    # Workflow stages
    if st.session_state.workflow_stage == "input":
        # ========== INPUT STAGE ==========
        st.markdown("---")
        st.markdown("## 📝 Step 1: Provide Input")
        
        client_info_dict = render_client_info_form()
        answers_list, client_info_from_sheet = render_questionnaire_answers_form()
        
        # Merge client info from sheet if available
        if client_info_from_sheet:
            st.info("📊 Client information detected from Google Sheet")
            if st.checkbox("Use client info from Google Sheet"):
                if client_info_from_sheet.get('customer_name'):
                    client_info_dict['customer_name'] = client_info_from_sheet['customer_name']
                if client_info_from_sheet.get('requirements'):
                    client_info_dict['requirements'] = client_info_from_sheet['requirements']
        
        # Validate inputs
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 START SOW GENERATION", type="primary", use_container_width=True):
                if not client_info_dict['customer_name']:
                    st.error("❌ Customer name is required")
                elif not client_info_dict['requirements']:
                    st.error("❌ Project requirements are required")
                elif len(answers_list) == 0:
                    st.error("❌ At least one questionnaire answer is required")
                else:
                    # Create ClientInformation
                    client_info = ClientInformation(
                        customer_name=client_info_dict['customer_name'],
                        business_domain=client_info_dict['business_domain'],
                        requirements=client_info_dict['requirements'],
                        audience=client_info_dict['audience'],
                        language=client_info_dict['language'],
                        project_type=client_info_dict.get('project_type'),
                        budget_range=client_info_dict.get('budget_range'),
                        timeline=client_info_dict.get('timeline'),
                        additional_context=client_info_dict.get('additional_context')
                    )
                    
                    # Create QuestionnaireAnswers
                    questionnaire_answers = [
                        QuestionnaireAnswer(
                            question_id=ans['question_id'],
                            question_text=ans['question_text'],
                            section=ans['section'],
                            answer=ans['answer']
                        )
                        for ans in answers_list
                    ]
                    
                    # Save to session state
                    st.session_state.client_info = client_info
                    st.session_state.questionnaire_answers = questionnaire_answers
                    st.session_state.workflow_stage = "phase1"
                    st.rerun()
    
    elif st.session_state.workflow_stage == "phase1":
        # ========== PHASE 1: AUTO-CORRECTION LOOP ==========
        st.markdown("---")
        st.markdown("## ⚙️ PHASE 1: Automated Generation with Quality Control")
        
        with st.spinner("🤖 AI Agent is working... (This may take 2-5 minutes)"):
            # Create orchestrator with config
            orchestrator = SOWOrchestrator(
                max_auto_retries=config_dict['max_auto_retries'],
                pass_threshold=config_dict['pass_threshold'],
                top_k=config_dict['top_k']
            )
            
            # Generate config
            gen_config = GenerationConfig(
                temperature=config_dict['temperature'],
                max_retries=config_dict['max_auto_retries']
            )
            
            # Run PHASE 1
            result = orchestrator.generate_complete_sow(
                st.session_state.client_info,
                st.session_state.questionnaire_answers,
                gen_config
            )
            
            # Save result
            st.session_state.result = result
            st.session_state.orchestrator = orchestrator
            st.session_state.workflow_stage = "phase2"
            st.rerun()
    
    elif st.session_state.workflow_stage == "phase2":
        # ========== PHASE 2: HUMAN REVIEW ==========
        st.markdown("---")
        st.markdown("## 👤 PHASE 2: Human Review & Feedback")
        
        result: OrchestrationResult = st.session_state.result
        
        if result.status == "failure":
            st.error(f"❌ Generation failed at {result.failed_component}")
            st.error(f"Error: {result.error_message}")
            if st.button("🔄 Start Over"):
                st.session_state.workflow_stage = "input"
                st.rerun()
            return
        
        # Display all 3 components with separate feedback
        tabs = st.tabs(["📋 Project Detail", "📊 Project Assumptions", "📝 Scope of Work"])
        
        with tabs[0]:
            render_project_detail(result.project_detail, result.detail_judge)
            st.markdown("### 💬 Feedback for Project Detail")
            detail_feedback = st.text_area(
                "Provide feedback to improve this component:",
                key="detail_feedback",
                height=100,
                placeholder="e.g., Add more details about feature X, Remove feature Y, etc."
            )
            if st.button("🔄 Regenerate Project Detail", key="regen_detail"):
                if detail_feedback:
                    with st.spinner("Regenerating with cascade..."):
                        new_result = st.session_state.orchestrator.handle_feedback(
                            target_component="project_detail",
                            feedback=detail_feedback,
                            current_detail=result.project_detail,
                            current_assumption=result.project_assumption,
                            current_sow=result.scope_of_work,
                            client_info=st.session_state.client_info,
                            questionnaire_answers=st.session_state.questionnaire_answers,
                            config=GenerationConfig(temperature=config_dict['temperature'])
                        )
                        st.session_state.result = new_result
                        st.rerun()
                else:
                    st.warning("Please provide feedback before regenerating")
        
        with tabs[1]:
            render_project_assumption(result.project_assumption, result.assumption_judge)
            st.markdown("### 💬 Feedback for Project Assumptions")
            assumption_feedback = st.text_area(
                "Provide feedback to improve this component:",
                key="assumption_feedback",
                height=100,
                placeholder="e.g., Modify assumption about data scope, Add section for X, etc."
            )
            if st.button("🔄 Regenerate Project Assumptions", key="regen_assumption"):
                if assumption_feedback:
                    with st.spinner("Regenerating with cascade..."):
                        new_result = st.session_state.orchestrator.handle_feedback(
                            target_component="project_assumption",
                            feedback=assumption_feedback,
                            current_detail=result.project_detail,
                            current_assumption=result.project_assumption,
                            current_sow=result.scope_of_work,
                            client_info=st.session_state.client_info,
                            questionnaire_answers=st.session_state.questionnaire_answers,
                            config=GenerationConfig(temperature=config_dict['temperature'])
                        )
                        st.session_state.result = new_result
                        st.rerun()
                else:
                    st.warning("Please provide feedback before regenerating")
        
        with tabs[2]:
            render_scope_of_work(result.scope_of_work, result.sow_judge)
            st.markdown("### 💬 Feedback for Scope of Work")
            sow_feedback = st.text_area(
                "Provide feedback to improve this component:",
                key="sow_feedback",
                height=100,
                placeholder="e.g., Add tasks for testing, Reduce man-days for X, etc."
            )
            if st.button("🔄 Regenerate Scope of Work", key="regen_sow"):
                if sow_feedback:
                    with st.spinner("Regenerating..."):
                        new_result = st.session_state.orchestrator.handle_feedback(
                            target_component="scope_of_work",
                            feedback=sow_feedback,
                            current_detail=result.project_detail,
                            current_assumption=result.project_assumption,
                            current_sow=result.scope_of_work,
                            client_info=st.session_state.client_info,
                            questionnaire_answers=st.session_state.questionnaire_answers,
                            config=GenerationConfig(temperature=config_dict['temperature'])
                        )
                        st.session_state.result = new_result
                        st.rerun()
                else:
                    st.warning("Please provide feedback before regenerating")
        
        # Approve button
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("✅ APPROVE ALL COMPONENTS", type="primary", use_container_width=True):
                st.session_state.workflow_stage = "approved"
                st.rerun()
    
    elif st.session_state.workflow_stage == "approved":
        # ========== PHASE 4: APPROVED ==========
        st.markdown("---")
        st.markdown("## ✅ PHASE 4: Approved & Export")
        st.success("🎉 All components have been approved!")
        
        result: OrchestrationResult = st.session_state.result
        
        # Export options
        st.markdown("### 📥 Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export to Google Sheets
            st.markdown("**📊 Export to Google Sheets**")
            
            credentials_ok = bool(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
            
            if credentials_ok:
                sheet_url = st.text_input(
                    "Google Sheet URL:",
                    placeholder="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
                    help="Share the sheet with service account first!",
                    key="sow_sheet_url_input"
                )
                
                overview_ws_name = st.text_input(
                    "Overview Worksheet Name:",
                    value="Overview",
                    key="overview_ws_name"
                )
                
                sow_ws_name = st.text_input(
                    "SOW Worksheet Name:",
                    value="Scope of Work",
                    key="sow_ws_name"
                )
                
                if st.button("📊 Export to Sheets", type="primary", use_container_width=True, key="export_sow_sheets"):
                    if not sheet_url:
                        st.error("❌ Please provide a Google Sheet URL!")
                    elif not overview_ws_name.strip() or not sow_ws_name.strip():
                        st.error("❌ Please provide worksheet names!")
                    else:
                        with st.spinner("🔄 Exporting SOW to Google Sheets..."):
                            try:
                                connector = SOWGoogleSheetsConnector()
                                export_result = connector.export_sow_to_sheet(
                                    spreadsheet_url=sheet_url,
                                    project_detail=result.project_detail,
                                    project_assumption=result.project_assumption,
                                    scope_of_work=result.scope_of_work,
                                    overview_worksheet_name=overview_ws_name.strip(),
                                    sow_worksheet_name=sow_ws_name.strip()
                                )
                                
                                if export_result.success:
                                    st.success(f"✅ {export_result.message}")
                                    st.markdown(f"[🔗 Open Sheet]({export_result.spreadsheet_url})")
                                    st.balloons()
                                else:
                                    st.error(f"❌ Export failed: {export_result.error_message}")
                                    if "Cannot access" in export_result.error_message:
                                        st.info("💡 Make sure you shared the sheet with the service account!")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                                logger.error(f"Export error: {str(e)}")
            else:
                st.text_input("Google Sheet URL:", disabled=True)
                st.text_input("Overview Worksheet Name:", disabled=True, value="Overview")
                st.text_input("SOW Worksheet Name:", disabled=True, value="Scope of Work")
                st.button("📊 Export to Sheets", disabled=True, use_container_width=True)
                st.caption("⚠️ Configure GOOGLE_APPLICATION_CREDENTIALS in .env")
        
        with col2:
            # Export as JSON
            st.markdown("**📄 Download JSON**")
            
            export_data = {
                "customer_name": result.project_detail.customer_name,
                "generated_at": datetime.now().isoformat(),
                "project_detail": result.project_detail.to_dict(),
                "project_assumption": result.project_assumption.to_dict(),
                "scope_of_work": result.scope_of_work.to_dict(),
                "judge_scores": {
                    "project_detail": result.detail_judge.score,
                    "project_assumption": result.assumption_judge.score,
                    "scope_of_work": result.sow_judge.score
                }
            }
            
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📄 Download JSON",
                data=json_str,
                file_name=f"sow_{result.project_detail.customer_name}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col3:
            # Start new generation
            st.markdown("**🔄 New Generation**")
            if st.button("🔄 Start New", use_container_width=True):
                # Clear session state
                for key in ['orchestrator', 'client_info', 'questionnaire_answers', 'result']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.workflow_stage = "input"
                st.rerun()


if __name__ == "__main__":
    main()
