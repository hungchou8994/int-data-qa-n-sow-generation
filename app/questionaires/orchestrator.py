import logging
from typing import Optional, Dict, Any
from .model import QuestionnaireInput, QuestionnaireOutput, GenerationConfig
from .engine import QuestionnaireEngine
from .judge import QuestionnaireJudge

logger = logging.getLogger(__name__)


class QuestionnaireOrchestrator:
    
    def __init__(
        self,
        google_api_key: str,
        max_auto_retries: int = 3,
        pass_threshold: int = 75
    ):
        self.engine = QuestionnaireEngine(google_api_key)
        self.judge = QuestionnaireJudge(google_api_key, pass_threshold=pass_threshold)
        self.max_auto_retries = max_auto_retries
        self.pass_threshold = pass_threshold
        logger.info(f"QuestionnaireOrchestrator initialized (max_retries={max_auto_retries}, threshold={pass_threshold})")
    
    def generate_with_validation(
        self,
        input_data: QuestionnaireInput,
        config: Optional[GenerationConfig] = None
    ) -> Dict[str, Any]:
        if config is None:
            config = GenerationConfig()
        
        logger.info(f"🚀 Starting questionnaire generation with validation for: {input_data.customer_name}")
        
        attempt = 0
        accumulated_feedback = ""
        previous_questionnaire = None
        
        while attempt < self.max_auto_retries:
            attempt += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"ATTEMPT {attempt}/{self.max_auto_retries}")
            logger.info(f"{'='*60}")
            
            try:
                # Generate questionnaire
                questionnaire, rag_questions = self.engine.generate_questionnaire(
                    input_data=input_data,
                    config=config,
                    previous_questionnaire=previous_questionnaire,
                    feedback=accumulated_feedback if accumulated_feedback else None
                )
                
                # Reuse RAG questions from engine (no duplicate call!)
                # Validate with judge
                judge_result = self.judge.judge_questionnaire(
                    questionnaire=questionnaire,
                    input_data=input_data,
                    rag_questions=rag_questions
                )
                
                # Check if passed
                if judge_result["status"] == "PASS":
                    logger.info(f"✅ Questionnaire PASSED on attempt {attempt}")
                    return {
                        "questionnaire": questionnaire,
                        "judge_result": judge_result,
                        "attempts": attempt,
                        "status": "success"
                    }
                
                # Failed - accumulate feedback for next attempt
                logger.warning(f"❌ Attempt {attempt} FAILED with score {judge_result['score']}/{self.pass_threshold}")
                
                if attempt < self.max_auto_retries:
                    # Prepare feedback for next attempt
                    accumulated_feedback += f"\n\n--- Feedback from Attempt {attempt} ---\n"
                    accumulated_feedback += f"Score: {judge_result['score']}/100\n"
                    accumulated_feedback += f"Issues: {judge_result['feedback']}\n"
                    
                    if judge_result.get('improvements'):
                        accumulated_feedback += "\nRequired Improvements:\n"
                        for imp in judge_result['improvements']:
                            accumulated_feedback += f"- {imp}\n"
                    
                    previous_questionnaire = questionnaire
                    logger.info(f"🔄 Preparing retry with accumulated feedback...")
                else:
                    # Max retries reached
                    logger.error(f"❌ Max retries ({self.max_auto_retries}) reached. Returning best attempt.")
                    return {
                        "questionnaire": questionnaire,
                        "judge_result": judge_result,
                        "attempts": attempt,
                        "status": "max_retries_reached",
                        "warning": f"Failed to achieve passing score after {self.max_auto_retries} attempts"
                    }
                    
            except Exception as e:
                logger.error(f"Error in attempt {attempt}: {str(e)}")
                if attempt >= self.max_auto_retries:
                    raise
        
        # Should not reach here
        raise RuntimeError("Unexpected end of generation loop")
    
    def regenerate_with_feedback(
        self,
        input_data: QuestionnaireInput,
        config: Optional[GenerationConfig],
        previous_questionnaire: QuestionnaireOutput,
        feedback: str
    ) -> Dict[str, Any]:

        if config is None:
            config = GenerationConfig()
        
        logger.info(f"🔄 Regenerating questionnaire with user feedback")
        logger.info(f"User feedback: {feedback[:100]}...")
        
        attempt = 0
        accumulated_feedback = f"User Feedback: {feedback}"
        current_questionnaire = previous_questionnaire
        
        while attempt < self.max_auto_retries:
            attempt += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"REGENERATION ATTEMPT {attempt}/{self.max_auto_retries}")
            logger.info(f"{'='*60}")
            
            try:
                # Regenerate
                questionnaire, rag_questions = self.engine.generate_questionnaire(
                    input_data=input_data,
                    config=config,
                    previous_questionnaire=current_questionnaire,
                    feedback=accumulated_feedback
                )
                
                # Reuse RAG questions from engine (no duplicate call!)
                # Validate
                judge_result = self.judge.judge_questionnaire(
                    questionnaire=questionnaire,
                    input_data=input_data,
                    rag_questions=rag_questions
                )
                
                # Check if passed
                if judge_result["status"] == "PASS":
                    logger.info(f"✅ Regenerated questionnaire PASSED on attempt {attempt}")
                    return {
                        "questionnaire": questionnaire,
                        "judge_result": judge_result,
                        "attempts": attempt,
                        "status": "success"
                    }
                
                # Failed
                logger.warning(f"❌ Regeneration attempt {attempt} FAILED with score {judge_result['score']}/{self.pass_threshold}")
                
                if attempt < self.max_auto_retries:
                    # Accumulate feedback
                    accumulated_feedback += f"\n\n--- Judge Feedback from Attempt {attempt} ---\n"
                    accumulated_feedback += f"Score: {judge_result['score']}/100\n"
                    accumulated_feedback += f"Issues: {judge_result['feedback']}\n"
                    
                    if judge_result.get('improvements'):
                        accumulated_feedback += "\nRequired Improvements:\n"
                        for imp in judge_result['improvements']:
                            accumulated_feedback += f"- {imp}\n"
                    
                    current_questionnaire = questionnaire
                else:
                    logger.error(f"❌ Max regeneration retries reached")
                    return {
                        "questionnaire": questionnaire,
                        "judge_result": judge_result,
                        "attempts": attempt,
                        "status": "max_retries_reached",
                        "warning": f"Failed to achieve passing score after {self.max_auto_retries} attempts"
                    }
                    
            except Exception as e:
                logger.error(f"Error in regeneration attempt {attempt}: {str(e)}")
                if attempt >= self.max_auto_retries:
                    raise
        
        raise RuntimeError("Unexpected end of regeneration loop")


def test_orchestrator():
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    input_data = QuestionnaireInput(
        customer_name="Cloud Ace",
        requirements="Build a real-time data analytics platform with AI/ML capabilities",
        business_domain="IT and Software Services",
        audience="Data Engineering Team",
        language="English",
        project_type="Data Analytics",
        timeline="3-6 months",
        budget_range="$50K - $100K"
    )
    
    config = GenerationConfig(
        max_questions=15,
        min_questions=10,
        retrieval_top_k=10,
        temperature=0.7
    )
    
    orchestrator = QuestionnaireOrchestrator(
        google_api_key=os.getenv('GOOGLE_API_KEY'),
        max_auto_retries=3,
        pass_threshold=75
    )
    
    result = orchestrator.generate_with_validation(input_data, config)
    
    print(f"\n{'='*80}")
    print(f"ORCHESTRATOR RESULT")
    print(f"{'='*80}")
    print(f"Status: {result['status']}")
    print(f"Attempts: {result['attempts']}")
    print(f"Judge Score: {result['judge_result']['score']}/100")
    print(f"Judge Status: {result['judge_result']['status']}")
    print(f"\nQuestionnaire: {result['questionnaire'].title}")
    print(f"Total Questions: {result['questionnaire'].total_questions}")
    print(f"\nJudge Feedback:\n{result['judge_result']['feedback']}")


if __name__ == "__main__":
    test_orchestrator()
