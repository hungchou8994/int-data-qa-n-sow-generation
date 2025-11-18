"""
Test script for questionnaire engine
"""
import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from questionaires.engine import QuestionnaireEngine
from questionaires.model import QuestionnaireInput, GenerationConfig

load_dotenv()

def test_api_key():
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        print(" Google API Key found")
        return True
    else:
        print("Google API Key not found")
        return False

def test_engine_initialization():
    """Test engine initialization"""
    try:
        engine = QuestionnaireEngine()
        print(" QuestionnaireEngine initialized successfully")
        return engine
    except Exception as e:
        print(f" Failed to initialize QuestionnaireEngine: {e}")
        return None

def test_questionnaire_generation(engine):
    """Test questionnaire generation with sample data"""
    if not engine:
        print(" Cannot test generation - engine not initialized")
        return None
    
    # Sample input data
    sample_input = QuestionnaireInput(
        customer_name="ABC Technology Company",
        requirements="We need to build a customer management system with CRM features, reporting dashboard, and mobile app integration",
        business_domain="Technology/Software",
        audience="IT Team and Management",
        project_type="Custom Software Development",
        budget_range="$50,000 - $100,000",
        timeline="6 months",
        additional_context="The company has 50+ employees and needs to integrate with existing ERP system",
        language="Vietnamese"
    )
    
    # Custom config for testing
    test_config = GenerationConfig(
        max_questions=20,
        min_questions=15,
        retrieval_top_k=10,
        temperature=0.7
    )
    
    try:
        print("\n Generating questionnaire...")
        print(f"Customer: {sample_input.customer_name}")
        print(f"Domain: {sample_input.business_domain}")
        print(f"Requirements: {sample_input.requirements[:100]}...")
        
        questionnaire = engine.generate_questionnaire(sample_input, test_config)
        
        print(f"\n Questionnaire generated successfully!")
        print(f"Title: {questionnaire.title}")
        print(f"Description: {questionnaire.description}")
        print(f"Total Questions: {questionnaire.total_questions}")
        print(f"Customer: {questionnaire.customer_name}")
        print(f"Business Domain: {questionnaire.business_domain}")
        print(f"Audience: {questionnaire.audience}")
        
        print(f"\n📋 Generated Questions:")
        for i, question in enumerate(questionnaire.questions, 1):
            print(f"\n{i}. [{question.section}] {question.id}")
            if question.title:
                print(f"   Title: {question.title}")
            print(f"   Question: {question.question_text}")
            if question.similarity_score:
                print(f"   Similarity Score: {question.similarity_score:.3f}")
        
        return questionnaire
        
    except Exception as e:
        print(f" Failed to generate questionnaire: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_different_scenarios(engine):
    """Test with different business scenarios"""
    if not engine:
        return
    
    scenarios = [
        {
            "name": "E-commerce Platform",
            "input": QuestionnaireInput(
                customer_name="Online Retail Store",
                requirements="Build an e-commerce platform with payment integration, inventory management, and customer reviews",
                business_domain="E-commerce/Retail",
                audience="Business Owners and Developers",
                project_type="Web Application",
                budget_range="$30,000 - $60,000",
                timeline="4 months"
            )
        },
        {
            "name": "Healthcare Management",
            "input": QuestionnaireInput(
                customer_name="City Medical Center",
                requirements="Patient management system with appointment scheduling, medical records, and billing",
                business_domain="Healthcare",
                audience="Medical Staff and Administrators",
                project_type="Healthcare Software",
                budget_range="$80,000 - $150,000",
                timeline="8 months"
            )
        }
    ]
    
    print(f"\n Testing different scenarios...")
    
    for scenario in scenarios:
        print(f"\n--- Testing: {scenario['name']} ---")
        try:
            config = GenerationConfig(max_questions=6, min_questions=4)
            questionnaire = engine.generate_questionnaire(scenario['input'], config)
            print(f" {scenario['name']}: Generated {len(questionnaire.questions)} questions")
        except Exception as e:
            print(f" {scenario['name']}: Failed - {e}")

def main():
    """Main test function"""
    print("Starting Questionnaire Engine Tests\n")
    
    # Test 1: API Key
    if not test_api_key():
        print("\n  Please set GOOGLE_API_KEY environment variable")
        return
    
    # Test 2: Engine Initialization
    engine = test_engine_initialization()
    if not engine:
        return
    
    # Test 3: Basic Generation
    questionnaire = test_questionnaire_generation(engine)
    
    # Test 4: Different Scenarios
    #test_different_scenarios(engine)
    
    print(f"\n Testing completed!")
    
    if questionnaire:
        # Save sample output for review
        output_file = "sample_questionnaire_output.json"
        try:
            # Convert to dict for JSON serialization
            output_data = {
                "questionnaire_id": questionnaire.questionnaire_id,
                "title": questionnaire.title,
                "description": questionnaire.description,
                "customer_name": questionnaire.customer_name,
                "business_domain": questionnaire.business_domain,
                "audience": questionnaire.audience,
                "total_questions": questionnaire.total_questions,
                "created_at": questionnaire.created_at.isoformat(),
                "questions": [
                    {
                        "id": q.id,
                        "section": q.section,
                        "question_text": q.question_text,
                        "required": q.required,
                        "title": q.title,
                        "options": q.options,
                        "similarity_score": q.similarity_score
                    } for q in questionnaire.questions
                ]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f" Sample output saved to: {output_file}")
        except Exception as e:
            print(f"  Could not save output file: {e}")

if __name__ == "__main__":
    main()