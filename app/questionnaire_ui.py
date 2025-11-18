import streamlit as st
import logging
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from questionaires.model import QuestionnaireInput, GenerationConfig, QuestionnaireOutput
    from questionaires.orchestrator import QuestionnaireOrchestrator
    from sheet.model import QuestionnaireResponse, SheetOperation
    from sheet.connect import GoogleSheetsConnector
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.stop()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AI Questionnaire Generator",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2e8b57;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .question-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .similarity-score {
        background-color: #e3f2fd;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-size: 0.8rem;
        color: #1565c0;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    if 'questionnaire' not in st.session_state:
        st.session_state.questionnaire = None    
    if 'generation_history' not in st.session_state:
        st.session_state.generation_history = []
    if 'last_input_data' not in st.session_state:
        st.session_state.last_input_data = None
    if 'last_config' not in st.session_state:
        st.session_state.last_config = None
    if 'judge_result' not in st.session_state:
        st.session_state.judge_result = None


def render_sidebar():
    st.sidebar.title("⚙️ Configuration")
    
    st.sidebar.subheader("API Settings")
    
    default_api_key = os.getenv('GOOGLE_API_KEY', '')
    
    if default_api_key:
        st.sidebar.success("✅ API Key loaded from .env file")
    google_api_key = default_api_key
    if hasattr(st.session_state, 'use_manual_key') and st.session_state.use_manual_key:
        google_api_key = st.sidebar.text_input(
            "Manual API Key",
            type="password",
            help="Enter your Google API key manually"
        )
    
    st.sidebar.subheader("Generation Settings")
    max_questions = st.sidebar.slider("Max Questions", 5, 40, 20)
    min_questions = st.sidebar.slider("Min Questions", 5, 20, 10)
    retrieval_top_k = st.sidebar.slider("Retrieval Top-K", 5, 20, 10)
    similarity_threshold = st.sidebar.slider("Similarity Threshold", 0.5, 1.0, 0.7)
    temperature = st.sidebar.slider("LLM Temperature", 0.0, 1.0, 0.7)
    
    # Judge Settings
    st.sidebar.subheader("🧑‍⚖️ Judge Settings")
    pass_threshold = st.sidebar.slider(
        "Pass Threshold", 
        min_value=50, 
        max_value=100, 
        value=75, 
        step=5,
        help="Minimum score (0-100) for questionnaire to pass automatic validation"
    )
    
    max_retries = st.sidebar.slider(
        "Max Auto Retries",
        min_value=1,
        max_value=5,
        value=3,
        help="Maximum number of automatic retry attempts if judge fails"
    )
    
    if pass_threshold >= 80:
        st.sidebar.warning("⚠️ High threshold may cause frequent retries")
    else:
        st.sidebar.info(f"Questionnaires must score ≥ {pass_threshold}/100 to pass")
    
    # Google Sheets Configuration
    st.sidebar.subheader("📊 Google Sheets")
    
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if credentials_path and os.path.exists(credentials_path):
        st.sidebar.success("✅ Credentials configured")
    else:
        st.sidebar.warning("⚠️ Credentials not found")
        with st.sidebar.expander("Setup Instructions"):
            st.markdown("""
            1. Create service account in [Google Cloud Console](https://console.cloud.google.com/)
            2. Download JSON key file
            3. Set `GOOGLE_APPLICATION_CREDENTIALS` in .env
            4. Share your sheet with service account email
            """)
    
    
    
    return {
        'google_api_key': google_api_key,
        'max_questions': max_questions,
        'min_questions': min_questions,
        'retrieval_top_k': retrieval_top_k,
        'similarity_threshold': similarity_threshold,
        'temperature': temperature,
        'pass_threshold': pass_threshold,
        'max_retries': max_retries
    }


def render_input_form():
    st.markdown('<h2 class="section-header">📝 Project Requirements</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        customer_name = st.text_input(
            "Customer Name *",
            placeholder="e.g., Cloud Ace Corporation"
        )
        
        business_domain = st.selectbox(
            "Business Domain *",
            [
                "IT and Software Services",
                "Healthcare",
                "Finance and Banking",
                "E-commerce",
                "Manufacturing",
                "Education",
                "Real Estate",
                "Consulting",
                "Other"
            ]
        )
        
        audience = st.text_input(
            "Target Audience *",
            placeholder="e.g., IT Team, Management, End Users"
        )
    
        project_type = st.selectbox(
            "Project Type",
            [
                "Web Application",
                "Mobile Application",
                "Data Analytics",
                "AI/ML Solution",
                "Cloud Migration",
                "System Integration",
                "Custom Software",
                "Other"
            ]
        )
    
    with col2:
        budget_range = st.selectbox(
            "Budget Range",
            [
                "Not specified",
                "Under $10K",
                "$10K - $50K",
                "$50K - $100K",
                "$100K - $500K",
                "Over $500K",
            ]
        )
        
        timeline = st.selectbox(
            "Timeline",
            [
                "Not specified",
                "1-3 months",
                "3-6 months",
                "6-12 months",
                "Over 1 year",
            ]
        )
        language = st.selectbox("Language", ["English", "Vietnamese", "Other"])
    
    requirements = st.text_area(
        "Project Requirements *",
        placeholder="Describe your project requirements, goals, and specific needs...",
        height=100
    )
    
    additional_context = st.text_area(
        "Additional Context",
        placeholder="Any additional information that might help generate better questions...",
        height=80
    )
    
    return {
        'customer_name': customer_name,
        'business_domain': business_domain,
        'audience': audience,
        'language': language,
        'project_type': project_type,
        'budget_range': budget_range,
        'timeline': timeline,
        'requirements': requirements,
        'additional_context': additional_context
    }


def generate_questionnaire(input_data: Dict[str, Any], config: Dict[str, Any],
                        previous_questionnaire: Optional[QuestionnaireOutput] = None,
                        feedback: Optional[str] = None):
    try:
        # Validate required fields
        if not input_data['customer_name'] or not input_data['requirements'] or not input_data['audience']:
            st.error("Please fill in all required fields (Customer Name, Requirements, and Target Audience)")
            return None
        
        if not config['google_api_key']:
            st.error("Please provide a Google API key in the sidebar")
            return None
        
        # Create input object
        questionnaire_input = QuestionnaireInput(
            customer_name=input_data['customer_name'],
            requirements=input_data['requirements'],
            business_domain=input_data['business_domain'],
            audience=input_data['audience'],
            language=input_data['language'],
            project_type=input_data.get('project_type') if input_data.get('project_type') != "Other" else None,
            budget_range=input_data.get('budget_range') if input_data.get('budget_range') != "Not specified" else None,
            timeline=input_data.get('timeline') if input_data.get('timeline') != "Not specified" else None,
            additional_context=input_data.get('additional_context') or None
        )
        
        # Create generation config
        generation_config = GenerationConfig(
            max_questions=config['max_questions'],
            min_questions=config['min_questions'],
            retrieval_top_k=config['retrieval_top_k'],
            similarity_threshold=config['similarity_threshold'],
            temperature=config['temperature']
        )
        
        # Initialize orchestrator and generate with validation
        orchestrator = QuestionnaireOrchestrator(
            google_api_key=config['google_api_key'],
            max_auto_retries=config['max_retries'],
            pass_threshold=config['pass_threshold']
        )
        
        # Choose generation or regeneration
        if previous_questionnaire and feedback:
            with st.spinner("🔄 Regenerating questionnaire with feedback and validation..."):
                result = orchestrator.regenerate_with_feedback(
                    input_data=questionnaire_input,
                    config=generation_config,
                    previous_questionnaire=previous_questionnaire,
                    feedback=feedback
                )
        else:
            with st.spinner("🤖 Generating questionnaire with automatic validation..."):
                result = orchestrator.generate_with_validation(
                    input_data=questionnaire_input,
                    config=generation_config
                )
        
        # Store judge result in session state
        st.session_state.judge_result = result.get('judge_result')
        
        # Show result status
        judge_result = result.get('judge_result', {})
        if result['status'] == 'success':
            st.success(f"✅ Generated successfully! Score: {judge_result.get('score', 0)}/100 (Attempts: {result['attempts']})")
        elif result['status'] == 'max_retries_reached':
            st.warning(f"⚠️ {result.get('warning', 'Max retries reached')} (Best: {judge_result.get('score', 0)}/100)")
        
        return result['questionnaire']
        
    except Exception as e:
        st.error(f"Error generating questionnaire: {str(e)}")
        logger.error(f"Error generating questionnaire: {str(e)}")
        return None


def render_questionnaire(questionnaire):
    """Render the generated questionnaire with judge results"""
    st.markdown('<h2 class="section-header">📋 Generated Questionnaire</h2>', unsafe_allow_html=True)
    
    # Judge Results (if available)
    if st.session_state.judge_result:
        judge = st.session_state.judge_result
        
        # Judge score display
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            score_color = "🟢" if judge['status'] == "PASS" else "🔴"
            st.metric(f"{score_color} Judge Score", f"{judge['score']}/100")
        with col2:
            st.metric("Status", judge['status'])
        with col3:
            if judge.get('breakdown'):
                avg_breakdown = sum(judge['breakdown'].values()) / len(judge['breakdown'])
                st.metric("Avg Category", f"{avg_breakdown:.1f}")
        with col4:
            st.metric("Total Questions", questionnaire.total_questions)
        
        # Judge feedback
        with st.expander("🧑‍⚖️ Judge Evaluation Details", expanded=(judge['status'] == "FAIL")):
            st.markdown("**Overall Feedback:**")
            st.info(judge['feedback'])
            
            if judge.get('breakdown'):
                st.markdown("**Score Breakdown:**")
                cols = st.columns(4)
                breakdown_items = list(judge['breakdown'].items())
                for i, (category, score) in enumerate(breakdown_items):
                    with cols[i % 4]:
                        st.metric(category.title(), f"{score}/100")
            
            if judge.get('strengths'):
                st.markdown("**✅ Strengths:**")
                for strength in judge['strengths']:
                    st.markdown(f"- {strength}")
            
            if judge.get('improvements'):
                st.markdown("**⚠️ Areas for Improvement:**")
                for improvement in judge['improvements']:
                    st.markdown(f"- {improvement}")
        
        st.markdown("---")
    
    # Questionnaire header
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Customer", questionnaire.customer_name)
    with col2:
        st.metric("Domain", questionnaire.business_domain)
    with col3:
        st.metric("Created", questionnaire.created_at.strftime("%Y-%m-%d %H:%M"))
    
    st.markdown(f"**Title:** {questionnaire.title}")
    st.markdown(f"**Description:** {questionnaire.description}")
    st.markdown(f"**Audience:** {questionnaire.audience}")
    st.markdown(f"**Language:** {questionnaire.language}")
    
    # Group questions by section
    sections = {}
    for question in questionnaire.questions:
        section = question.section
        if section not in sections:
            sections[section] = []
        sections[section].append(question)
    
    # Render questions by section
    for section_name, questions in sections.items():
        st.markdown(f"### {section_name}")
        
        for question in questions:
            with st.container():
                st.markdown(f'<div class="question-card">', unsafe_allow_html=True)
                
                # Question header with similarity score and source info if available
                if question.similarity_score or question.title:
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        if question.similarity_score:
                            st.markdown(
                                f'<span class="similarity-score">Score: {question.similarity_score:.3f}</span>',
                                unsafe_allow_html=True
                            )
                        if question.title:
                            st.caption(f"📋 Source: {question.title}")  
                
                st.markdown(question.question_text)
                st.markdown('</div>', unsafe_allow_html=True)
    



def render_history():
    """Render generation history"""
    if st.session_state.generation_history:
        st.markdown('<h2 class="section-header">📊 Generation History</h2>', unsafe_allow_html=True)
        
        for i, item in enumerate(reversed(st.session_state.generation_history)):
            with st.expander(f"Generation {len(st.session_state.generation_history) - i}: {item['customer_name']}"):
                st.write(f"**Domain:** {item['business_domain']}")
                st.write(f"**Language:** {item['language']}")
                st.write(f"**Questions:** {item['total_questions']}")
                st.write(f"**Generated:** {item['created_at']}")
                st.write(f"**Requirements:** {item['requirements'][:200]}...")


def main():
    """Main Streamlit application"""
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">🤖 AI Questionnaire Generator</h1>', unsafe_allow_html=True)
    st.markdown("Generate intelligent questionnaires using AI and historical data retrieval")
    
    # Sidebar configuration
    config = render_sidebar()
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["🔧 Generate", "📋 Review", "📊 History"])
    
    with tab1:
        # Input form
        input_data = render_input_form()
        
        # Generate button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Generate Questionnaire", type="primary", use_container_width=True):
                questionnaire = generate_questionnaire(input_data, config)
                if questionnaire:
                    st.session_state.questionnaire = questionnaire
                    
                    # ADDED: Save the input data for regeneration
                    st.session_state.last_input_data = input_data
                    st.session_state.last_config = config
                    
                    # Add to history
                    st.session_state.generation_history.append({
                        'customer_name': questionnaire.customer_name,
                        'business_domain': questionnaire.business_domain,
                        'language': questionnaire.language,
                        'total_questions': questionnaire.total_questions,
                        'created_at': questionnaire.created_at.strftime("%Y-%m-%d %H:%M"),
                        'requirements': input_data['requirements']
                    })
                    
                    st.success("✅ Questionnaire generated successfully! Check the Review tab.")
    
    with tab2:
        if st.session_state.questionnaire:
            render_questionnaire(st.session_state.questionnaire)
            st.markdown("---")
            st.markdown("### 🔄 Regenerate with Feedback")
            st.caption("Provide feedback to improve the questionnaire. The AI will use your feedback and current sidebar settings.")
            
            feedback_text = st.text_area(
                "Your feedback",
                placeholder="e.g., 'add more technical questions', 'make it simpler', 'focus on security'",
                key="feedback_input"
            )

            if st.button("🚀 Regenerate with Feedback", use_container_width=True):
                if not feedback_text:
                    st.warning("Please enter your feedback above.")
                elif not st.session_state.get('last_input_data'):
                    st.error("Could not find original data. Please generate from Tab 1 first.")
                else:
                    questionnaire = generate_questionnaire(
                        st.session_state.last_input_data,
                        config,
                        previous_questionnaire=st.session_state.questionnaire,
                        feedback=feedback_text
                    )
                    if questionnaire:
                        st.session_state.questionnaire = questionnaire
                        st.session_state.generation_history.append({
                            'customer_name': questionnaire.customer_name,
                            'business_domain': questionnaire.business_domain,
                            'language': questionnaire.language,
                            'total_questions': questionnaire.total_questions,
                            'created_at': questionnaire.created_at.strftime("%Y-%m-%d %H:%M"),
                            'requirements': f"(Feedback: {feedback_text[:50]}...) {st.session_state.last_input_data['requirements'][:100]}"
                        })
                        st.success("✅ Questionnaire regenerated successfully!")
                        st.rerun()

            st.markdown("---")
            st.markdown("### 💾 Export Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📊 Export to Google Sheets**")
                
                credentials_ok = bool(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
                
                if credentials_ok:
                    sheet_url = st.text_input(
                        "Google Sheet URL:",
                        placeholder="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
                        help="Share the sheet with service account first!",
                        key="sheet_url_input"
                    )
                    
                    worksheet_name = st.text_input(
                        "Worksheet Name:",
                        value="Questionnaire",
                        placeholder="e.g., Questionnaire, Survey_2024",
                        help="Name of the worksheet tab (will replace if exists)",
                        key="worksheet_name_input"
                    )
                    
                    if st.button("📊 Export to Sheets", type="primary", use_container_width=True):
                        if not sheet_url:
                            st.error("❌ Please provide a Google Sheet URL first!")
                        elif not worksheet_name or not worksheet_name.strip():
                            st.error("❌ Please provide a worksheet name!")
                        else:
                            with st.spinner("🔄 Exporting..."):
                                try:
                                    # Get original requirements from last_input_data if available
                                    original_requirements = None
                                    if st.session_state.get('last_input_data'):
                                        original_requirements = st.session_state.last_input_data.get('requirements')
                                    
                                    connector = GoogleSheetsConnector()
                                    result = connector.export_questionnaire_to_existing_sheet(
                                        spreadsheet_url=sheet_url,
                                        questionnaire=st.session_state.questionnaire,
                                        judge_result=st.session_state.judge_result,
                                        input_requirements=original_requirements,
                                        worksheet_name=worksheet_name.strip()
                                    )
                                    
                                    if result.success:
                                        st.success(f"✅ {result.message}")
                                        st.markdown(f"[🔗 Open Sheet]({result.spreadsheet_url})")
                                        st.balloons()
                                    else:
                                        st.error(f"❌ Export failed: {result.error_message}")
                                        if "Cannot access" in result.error_message:
                                            st.info("💡 Make sure you shared the sheet with the service account!")
                                except Exception as e:
                                    st.error(f"❌ Error: {str(e)}")
                                    logger.error(f"Export error: {str(e)}")
                else:
                    st.text_input("Google Sheet URL:", disabled=True)
                    st.text_input("Worksheet Name:", disabled=True, value="Questionnaire")
                    st.button("📊 Export to Sheets", disabled=True, use_container_width=True)
                    st.caption("⚠️ Configure GOOGLE_APPLICATION_CREDENTIALS in .env")
            
            with col2:
                st.markdown("**📥 Download JSON**")
                
                questionnaire_data = {
                    'id': st.session_state.questionnaire.questionnaire_id,
                    'title': st.session_state.questionnaire.title,
                    'description': st.session_state.questionnaire.description,
                    'customer_name': st.session_state.questionnaire.customer_name,
                    'business_domain': st.session_state.questionnaire.business_domain,
                    'audience': st.session_state.questionnaire.audience,
                    'language': st.session_state.questionnaire.language,
                    'total_questions': st.session_state.questionnaire.total_questions,
                    'created_at': st.session_state.questionnaire.created_at.isoformat(),
                    'questions': [
                        {
                            'id': q.id,
                            'section': q.section,
                            'question_text': q.question_text,
                            'title': q.title,
                            'similarity_score': q.similarity_score
                        }
                        for q in st.session_state.questionnaire.questions
                    ]
                }
                
                st.download_button(
                    label="📥 Download JSON",
                    data=json.dumps(questionnaire_data, indent=2, ensure_ascii=False),
                    file_name=f"questionnaire_{st.session_state.questionnaire.questionnaire_id}.json",
                    mime="application/json",
                    use_container_width=True
                )
        else:
            st.info("👈 Generate a questionnaire first in the Generate tab")
    
    with tab3:
        render_history()


if __name__ == "__main__":
    main()
