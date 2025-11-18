"""
Test script for exporting questionnaire to EXISTING Google Sheet
User provides a Google Sheet link, system writes formatted questionnaire to it
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from questionaires.model import QuestionnaireInput, QuestionnaireOutput, Question
from sheet.connect import GoogleSheetsConnector

load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)



def create_sample_questionnaire() -> QuestionnaireOutput:
    """Create a sample questionnaire for testing"""
    
    questions = [
        # Business Objectives
        Question(
            id="q1",
            section="Business Objectives & Scope",
            question_text="What is the primary business objective for the AI chatbot?\n(e.g., Reduce customer service workload, improve response time, 24/7 availability)",
            title="AI Chatbot Requirements"
        ),
        Question(
            id="q2",
            section="Business Objectives & Scope",
            question_text="What are the expected deliverables at the end of the project?\n(e.g., Deployed chatbot, training documentation, API integration)",
            title="AI Chatbot Requirements"
        ),
        Question(
            id="q3",
            section="Business Objectives & Scope",
            question_text="What specific bank policies should the chatbot be able to answer?\n(e.g., Loan policies, account opening, credit cards, investment products)",
            title="AI Chatbot Requirements"
        ),
        
        # Current Process
        Question(
            id="q4",
            section="Current Process & Challenges",
            question_text="How are customer policy questions currently handled?\n(e.g., Manual response by staff, email support, phone hotline)",
            title="AI Chatbot Requirements"
        ),
        Question(
            id="q5",
            section="Current Process & Challenges",
            question_text="What are the main pain points in the current process?\n(e.g., Long response time, inconsistent answers, high staff workload)",
            title="AI Chatbot Requirements"
        ),
        
        # Data Sources & Infrastructure
        Question(
            id="q6",
            section="Data Sources & Infrastructure",
            question_text="Where are the bank policy documents currently stored?\n(e.g., SharePoint, Google Drive, internal wiki, PDF files)",
            title="AI Chatbot Requirements"
        ),
        Question(
            id="q7",
            section="Data Sources & Infrastructure",
            question_text="What is the format of the policy documents?\n(e.g., PDF, Word, HTML, structured database)",
            title="AI Chatbot Requirements"
        ),
        Question(
            id="q8",
            section="Data Sources & Infrastructure",
            question_text="Are there any security or compliance requirements for handling customer data?\n(e.g., GDPR, data encryption, access control)",
            title="AI Chatbot Requirements"
        ),
        Question(
            id="q9",
            section="Data Sources & Infrastructure",
            question_text="What is the preferred deployment platform?\n(e.g., On-premise servers, Google Cloud, AWS, hybrid)",
            title="AI Chatbot Requirements"
        ),
        
        # Technical Requirements
        Question(
            id="q10",
            section="Technical Requirements",
            question_text="What channels should the chatbot support?\n(e.g., Website widget, mobile app, Facebook Messenger, LINE)",
            title="AI Chatbot Requirements"
        ),
        Question(
            id="q11",
            section="Technical Requirements",
            question_text="What languages should the chatbot support?\n(e.g., Vietnamese, English, both)",
            title="AI Chatbot Requirements"
        ),
        Question(
            id="q12",
            section="Technical Requirements",
            question_text="Should the chatbot integrate with existing systems?\n(e.g., CRM, ticketing system, customer database)",
            title="AI Chatbot Requirements"
        ),
        
        # Success Criteria
        Question(
            id="q13",
            section="Metrics & Success Criteria",
            question_text="How will you measure the success of the chatbot?\n(e.g., Response accuracy rate, user satisfaction score, reduction in support tickets)",
            title="AI Chatbot Requirements"
        ),
        Question(
            id="q14",
            section="Metrics & Success Criteria",
            question_text="Who will be responsible for validating the final chatbot performance?",
            title="AI Chatbot Requirements"
        ),
        
        # Timeline & Budget
        Question(
            id="q15",
            section="Timeline & Budget",
            question_text="What is the desired project timeline or delivery date?",
            title="AI Chatbot Requirements"
        ),
    ]
    
    return QuestionnaireOutput(
        questionnaire_id="test-vietcombank-001",
        title="AI Chatbot for Bank Policy: Requirements Questionnaire for Vietcombank",
        description="This questionnaire gathers essential requirements for building an AI chatbot to answer bank policy questions for Vietcombank customers.",
        customer_name="Vietcombank",
        business_domain="Banking & Financial Services",
        audience="IT Department, Customer Service Team",
        language="English",
        questions=questions,
        created_at=datetime.now(),
        total_questions=len(questions)
    )


def test_export_to_existing_sheet():
    """Test exporting to an existing Google Sheet"""
    
    print("\n" + "="*60)
    print("TESTING EXPORT TO EXISTING GOOGLE SHEET")
    print("="*60)
    
    # Check credentials
    creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if creds:
        print(f"✅ Using credentials: {creds}\n")
    else:
        print("❌ No credentials found. Set GOOGLE_APPLICATION_CREDENTIALS\n")
        return
    
    try:
        # Create sample questionnaire
        questionnaire = create_sample_questionnaire()
        print(f"📋 Created sample questionnaire:")
        print(f"   - Customer: {questionnaire.customer_name}")
        print(f"   - Title: {questionnaire.title}")
        print(f"   - Total Questions: {questionnaire.total_questions}")
        print()
        
        # Mock judge result (optional)
        judge_result = {
            "status": "PASS",
            "score": 85,
            "feedback": "Excellent questionnaire with comprehensive coverage of all key areas.",
            "breakdown": {
                "relevance": 28,
                "completeness": 22,
                "quality": 23,
                "diversity": 12
            },
            "strengths": [
                "Questions directly address AI chatbot requirements for banking",
                "Good coverage of technical, business, and compliance aspects",
                "Clear examples provided for each question"
            ],
            "improvements": [
                "Could add questions about maintenance and updates",
                "Consider adding questions about user training"
            ]
        }
        
        # Initialize connector
        connector = GoogleSheetsConnector()
        
        # User provides Google Sheet link
        print("="*60)
        print("OPTION 1: Enter Google Sheet URL")
        print("="*60)
        sheet_url = input("Paste your Google Sheet URL (or press Enter to use spreadsheet ID): ").strip()
        
        if sheet_url:
            # Extract spreadsheet ID from URL
            if "spreadsheets/d/" in sheet_url:
                spreadsheet_id = sheet_url.split("spreadsheets/d/")[1].split("/")[0]
            else:
                spreadsheet_id = sheet_url
        else:
            print("\nOPTION 2: Enter Spreadsheet ID directly")
            spreadsheet_id = input("Enter spreadsheet ID: ").strip()
        
        if not spreadsheet_id:
            print("❌ No spreadsheet ID provided!")
            return
        
        print(f"\n📊 Using spreadsheet ID: {spreadsheet_id}")
        
        # Export to existing sheet
        print("\n🚀 Exporting questionnaire to Google Sheet...")
        result = connector.export_questionnaire_to_existing_sheet(
            spreadsheet_url=spreadsheet_id,
            questionnaire=questionnaire,
            judge_result=judge_result
        )
        
        # Show result
        print("\n" + "="*60)
        if result.success:
            print(f"✅ SUCCESS!")
            print(f"   {result.message}")
            if result.spreadsheet_url:
                print(f"\n📎 Open your sheet:")
                print(f"   {result.spreadsheet_url}")
        else:
            print(f"❌ FAILED!")
            print(f"   Error: {result.error_message}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print()


def quick_test_with_id():
    """Quick test with hardcoded spreadsheet ID"""
    
    # FOR QUICK TESTING: Put your spreadsheet ID here
    TEST_SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"
    
    if TEST_SPREADSHEET_ID == "YOUR_SPREADSHEET_ID_HERE":
        print("⚠️  Please set TEST_SPREADSHEET_ID in the script first!")
        return
    
    questionnaire = create_sample_questionnaire()
    connector = GoogleSheetsConnector()
    
    result = connector.export_questionnaire_to_existing_sheet(
        spreadsheet_url=TEST_SPREADSHEET_ID,
        questionnaire=questionnaire
    )
    
    if result.success:
        print(f"✅ {result.message}")
        print(f"🔗 {result.spreadsheet_url}")
    else:
        print(f"❌ {result.error_message}")


if __name__ == "__main__":
    # Interactive test
    test_export_to_existing_sheet()
    
    # Or use quick test:
    # quick_test_with_id()
