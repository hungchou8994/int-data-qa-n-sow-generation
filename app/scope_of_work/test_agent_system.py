"""
Test script for SOW Agent System
Tests individual components and full workflow
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scope_of_work.model import (
    ClientInformation,
    QuestionnaireAnswer,
    GenerationConfig
)
from scope_of_work.engine import SOWEngine
from scope_of_work.judge import SOWJudge
from scope_of_work.orchestrator import SOWOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


def create_sample_data():
    """Create sample client info and questionnaire answers"""
    client_info = ClientInformation(
        customer_name="TechCorp Vietnam",
        business_domain="E-commerce",
        requirements="Build a demand forecasting platform to predict product sales for 1000 SKUs using AI/ML",
        audience="Data Science Team, Business Analysts",
        language="English",
        project_type="Data Analytics",
        budget_range="$50K - $100K",
        timeline="3-6 months",
        additional_context="Company has 3 years of historical sales data in Dropbox CSV files"
    )
    
    questionnaire_answers = [
        QuestionnaireAnswer(
            question_id="Q1",
            question_text="What are the main business objectives?",
            section="Business Requirements",
            answer="Reduce inventory costs by 20% through accurate demand forecasting. Improve stock availability to 95%."
        ),
        QuestionnaireAnswer(
            question_id="Q2",
            question_text="What data sources are available?",
            section="Data",
            answer="Sales data (3 years), inventory data (2 years), operational data (1 year) - all in CSV files on Dropbox"
        ),
        QuestionnaireAnswer(
            question_id="Q3",
            question_text="How many products need forecasting?",
            section="Scope",
            answer="Up to 1000 SKUs (Stock Keeping Units). Focus on products with at least 3 years of consistent transaction history."
        ),
        QuestionnaireAnswer(
            question_id="Q4",
            question_text="What is the target accuracy?",
            section="Technical",
            answer="Target forecast accuracy of 80% for qualified SKUs (those with sufficient history and consistent transactions)"
        ),
        QuestionnaireAnswer(
            question_id="Q5",
            question_text="What is the expected output format?",
            section="Deliverables",
            answer="Looker Studio dashboards - one for evaluation (model performance) and one for predictions (forecasted demand)"
        ),
        QuestionnaireAnswer(
            question_id="Q6",
            question_text="Is this MVP or production?",
            section="Scope",
            answer="This is MVP version. Production-grade features like auto-scaling and advanced monitoring are out of scope."
        )
    ]
    
    return client_info, questionnaire_answers


def test_engine_components():
    """Test SOWEngine - individual component generation"""
    logger.info("=" * 60)
    logger.info("TEST 1: SOWEngine Component Generation")
    logger.info("=" * 60)
    
    client_info, questionnaire_answers = create_sample_data()
    engine = SOWEngine()
    config = GenerationConfig(temperature=0.7, max_retries=3)
    
    # Test Project Detail generation
    logger.info("\n📋 Testing Project Detail generation...")
    from scope_of_work.model import ProjectDetailInput
    detail_input = ProjectDetailInput(client_info, questionnaire_answers)
    
    try:
        project_detail = engine.generate_project_detail(detail_input, config)
        logger.info(f"✅ Project Detail generated successfully")
        logger.info(f"   - Overview length: {len(project_detail.overview)} chars")
        logger.info(f"   - Key features: {len(project_detail.key_features)}")
        logger.info(f"   - Customer: {project_detail.customer_name}")
    except Exception as e:
        logger.error(f"❌ Failed to generate Project Detail: {str(e)}")
        return False
    
    # Test Project Assumption generation
    logger.info("\n📊 Testing Project Assumption generation...")
    from scope_of_work.model import ProjectAssumptionInput
    assumption_input = ProjectAssumptionInput(client_info, questionnaire_answers, project_detail)
    
    try:
        project_assumption = engine.generate_project_assumption(assumption_input, config)
        logger.info(f"✅ Project Assumption generated successfully")
        logger.info(f"   - Sections: {len(project_assumption.assumptions)}")
        for section in project_assumption.assumptions:
            logger.info(f"     * {section.section}: {len(section.points)} points")
    except Exception as e:
        logger.error(f"❌ Failed to generate Project Assumption: {str(e)}")
        return False
    
    # Test Scope of Work generation
    logger.info("\n📝 Testing Scope of Work generation (with RAG)...")
    from scope_of_work.model import ScopeOfWorkInput
    sow_input = ScopeOfWorkInput(client_info, questionnaire_answers, project_detail, project_assumption)
    
    try:
        scope_of_work = engine.generate_scope_of_work(sow_input, config)
        logger.info(f"✅ Scope of Work generated successfully")
        logger.info(f"   - Total tasks: {scope_of_work.total_tasks}")
        logger.info(f"   - Total man-days: {scope_of_work.total_man_days}")
        logger.info(f"   - Categories: {len(scope_of_work.get_tasks_by_category())}")
        
        # Show RAG vs Generated tasks
        rag_count = sum(1 for t in scope_of_work.tasks if t.source == "rag")
        gen_count = sum(1 for t in scope_of_work.tasks if t.source == "generated")
        logger.info(f"   - RAG tasks: {rag_count}")
        logger.info(f"   - Generated tasks: {gen_count}")
    except Exception as e:
        logger.error(f"❌ Failed to generate Scope of Work: {str(e)}")
        return False
    
    logger.info("\n✅ All engine components working correctly")
    return True


def test_judge_system():
    """Test SOWJudge - quality control"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: SOWJudge Quality Control")
    logger.info("=" * 60)
    
    client_info, questionnaire_answers = create_sample_data()
    engine = SOWEngine()
    judge = SOWJudge()
    config = GenerationConfig(temperature=0.7)
    
    # Generate components to judge
    logger.info("\n📋 Generating components for judging...")
    from scope_of_work.model import ProjectDetailInput, ProjectAssumptionInput, ScopeOfWorkInput
    
    detail_input = ProjectDetailInput(client_info, questionnaire_answers)
    project_detail = engine.generate_project_detail(detail_input, config)
    
    assumption_input = ProjectAssumptionInput(client_info, questionnaire_answers, project_detail)
    project_assumption = engine.generate_project_assumption(assumption_input, config)
    
    sow_input = ScopeOfWorkInput(client_info, questionnaire_answers, project_detail, project_assumption)
    scope_of_work = engine.generate_scope_of_work(sow_input, config)
    
    # Test judge on each component
    logger.info("\n🔍 Judging Project Detail...")
    try:
        detail_judge = judge.judge_project_detail(project_detail, client_info, questionnaire_answers)
        logger.info(f"   Status: {detail_judge.status}")
        logger.info(f"   Score: {detail_judge.score}/100")
        logger.info(f"   Feedback: {detail_judge.feedback[:100]}...")
        logger.info(f"   Issues: {len(detail_judge.issues)}")
    except Exception as e:
        logger.error(f"❌ Judge failed on Project Detail: {str(e)}")
        return False
    
    logger.info("\n🔍 Judging Project Assumption...")
    try:
        assumption_judge = judge.judge_project_assumption(
            project_assumption, project_detail, client_info, questionnaire_answers
        )
        logger.info(f"   Status: {assumption_judge.status}")
        logger.info(f"   Score: {assumption_judge.score}/100")
        logger.info(f"   Feedback: {assumption_judge.feedback[:100]}...")
        logger.info(f"   Issues: {len(assumption_judge.issues)}")
    except Exception as e:
        logger.error(f"❌ Judge failed on Project Assumption: {str(e)}")
        return False
    
    logger.info("\n🔍 Judging Scope of Work...")
    try:
        # Need to retrieve RAG tasks for judge
        from rag.bq_vector import retrieve_similar_sow_tasks
        query = engine._build_rag_query(client_info, project_detail, project_assumption)
        rag_tasks = retrieve_similar_sow_tasks(
            query, top_k=20,
            credentials_path=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        )
        
        sow_judge = judge.judge_scope_of_work(
            scope_of_work, project_assumption, project_detail, rag_tasks
        )
        logger.info(f"   Status: {sow_judge.status}")
        logger.info(f"   Score: {sow_judge.score}/100")
        logger.info(f"   Feedback: {sow_judge.feedback[:100]}...")
        logger.info(f"   Issues: {len(sow_judge.issues)}")
    except Exception as e:
        logger.error(f"❌ Judge failed on Scope of Work: {str(e)}")
        return False
    
    logger.info("\n✅ Judge system working correctly")
    return True


def test_orchestrator_phase1():
    """Test SOWOrchestrator - PHASE 1 auto-correction loop"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: SOWOrchestrator PHASE 1 (Auto-Correction)")
    logger.info("=" * 60)
    
    client_info, questionnaire_answers = create_sample_data()
    orchestrator = SOWOrchestrator(max_auto_retries=2)  # Reduce retries for testing
    config = GenerationConfig(temperature=0.7)
    
    logger.info("\n🚀 Running full PHASE 1 workflow...")
    logger.info("   (This will take 2-5 minutes)")
    
    try:
        result = orchestrator.generate_complete_sow(
            client_info,
            questionnaire_answers,
            config
        )
        
        logger.info(f"\n✅ PHASE 1 completed")
        logger.info(f"   Status: {result.status}")
        logger.info(f"   Failed component: {result.failed_component}")
        
        if result.project_detail:
            logger.info(f"\n📋 Project Detail:")
            logger.info(f"   - Version: {result.detail_version}")
            logger.info(f"   - Judge score: {result.detail_judge.score}/100")
            logger.info(f"   - Judge status: {result.detail_judge.status}")
        
        if result.project_assumption:
            logger.info(f"\n📊 Project Assumption:")
            logger.info(f"   - Version: {result.assumption_version}")
            logger.info(f"   - Judge score: {result.assumption_judge.score}/100")
            logger.info(f"   - Judge status: {result.assumption_judge.status}")
        
        if result.scope_of_work:
            logger.info(f"\n📝 Scope of Work:")
            logger.info(f"   - Version: {result.sow_version}")
            logger.info(f"   - Judge score: {result.sow_judge.score}/100")
            logger.info(f"   - Judge status: {result.sow_judge.status}")
            logger.info(f"   - Tasks: {result.scope_of_work.total_tasks}")
            logger.info(f"   - Man-days: {result.scope_of_work.total_man_days}")
        
        # Check history
        logger.info(f"\n📚 History tracking:")
        logger.info(f"   - Detail history: {len(orchestrator.detail_history)} versions")
        logger.info(f"   - Assumption history: {len(orchestrator.assumption_history)} versions")
        logger.info(f"   - SoW history: {len(orchestrator.sow_history)} versions")
        
        if result.status == "success":
            logger.info("\n✅ Full workflow successful!")
            return True, result, orchestrator
        else:
            logger.warning(f"\n⚠️ Workflow completed with issues: {result.error_message}")
            return False, result, orchestrator
    
    except Exception as e:
        logger.error(f"❌ Orchestrator failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None, None


def test_orchestrator_cascade():
    """Test cascade regeneration with feedback"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Cascade Regeneration (PHASE 3)")
    logger.info("=" * 60)
    
    # First run PHASE 1 to get initial result
    logger.info("\n🚀 Running PHASE 1 first...")
    success, initial_result, orchestrator = test_orchestrator_phase1()
    
    if not success or initial_result.status != "success":
        logger.error("❌ Cannot test cascade - PHASE 1 failed")
        return False
    
    client_info, questionnaire_answers = create_sample_data()
    config = GenerationConfig(temperature=0.7)
    
    # Test Case 1: Regenerate Project Assumption (should cascade to SoW)
    logger.info("\n🔄 Test Case 1: Regenerating Project Assumption")
    logger.info("   Expected: PA regenerates, SoW cascades")
    
    feedback = "Add more specific metrics for data quality. Change timeline assumption to 4 months instead of 6."
    
    try:
        result = orchestrator.handle_feedback(
            target_component="project_assumption",
            feedback=feedback,
            current_detail=initial_result.project_detail,
            current_assumption=initial_result.project_assumption,
            current_sow=initial_result.scope_of_work,
            client_info=client_info,
            questionnaire_answers=questionnaire_answers,
            config=config
        )
        
        logger.info(f"   ✅ Cascade completed")
        logger.info(f"   - Detail version: {result.detail_version} (should be unchanged)")
        logger.info(f"   - Assumption version: {result.assumption_version} (should be v_human_1)")
        logger.info(f"   - SoW version: {result.sow_version} (should be v_human_1)")
        
        # Verify cascade worked
        if result.detail_version == initial_result.detail_version:
            logger.info("   ✅ Detail unchanged (correct)")
        else:
            logger.warning("   ⚠️ Detail changed (unexpected)")
        
        if result.assumption_version == "v_human_1":
            logger.info("   ✅ Assumption has new version (correct)")
        else:
            logger.warning(f"   ⚠️ Assumption version is {result.assumption_version} (expected v_human_1)")
        
        if result.sow_version == "v_human_1":
            logger.info("   ✅ SoW cascaded (correct)")
        else:
            logger.warning(f"   ⚠️ SoW version is {result.sow_version} (expected v_human_1)")
    
    except Exception as e:
        logger.error(f"❌ Cascade test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    logger.info("\n✅ Cascade regeneration working correctly")
    return True


def test_export():
    """Test JSON export"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Export Functionality")
    logger.info("=" * 60)
    
    success, result, orchestrator = test_orchestrator_phase1()
    
    if not success or result.status != "success":
        logger.error("❌ Cannot test export - PHASE 1 failed")
        return False
    
    try:
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
        
        # Save to file
        output_file = f"test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Export successful: {output_file}")
        logger.info(f"   File size: {os.path.getsize(output_file)} bytes")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Export failed: {str(e)}")
        return False


def run_all_tests():
    """Run all tests"""
    logger.info("\n" + "🧪" * 30)
    logger.info("SOW AGENT SYSTEM - COMPREHENSIVE TEST SUITE")
    logger.info("🧪" * 30)
    
    results = {}
    
    # Test 1: Engine components
    logger.info("\n▶️  Running Test 1...")
    results['engine'] = test_engine_components()
    
    # Test 2: Judge system
    logger.info("\n▶️  Running Test 2...")
    results['judge'] = test_judge_system()
    
    # Test 3: Orchestrator PHASE 1
    logger.info("\n▶️  Running Test 3...")
    success, _, _ = test_orchestrator_phase1()
    results['orchestrator_phase1'] = success
    
    # Test 4: Cascade regeneration
    logger.info("\n▶️  Running Test 4...")
    results['cascade'] = test_orchestrator_cascade()
    
    # Test 5: Export
    logger.info("\n▶️  Running Test 5...")
    results['export'] = test_export()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    logger.info("\n" + "=" * 60)
    logger.info(f"OVERALL: {total_passed}/{total_tests} tests passed")
    logger.info("=" * 60)
    
    return total_passed == total_tests


if __name__ == "__main__":
    # Run all tests
    all_passed = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)
