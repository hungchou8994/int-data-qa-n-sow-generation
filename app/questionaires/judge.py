import logging
import google.generativeai as genai
from typing import Dict, Any, List
from .model import QuestionnaireOutput, QuestionnaireInput, RetrievalResult

logger = logging.getLogger(__name__)


class QuestionnaireJudge:
    
    def __init__(self, google_api_key: str, pass_threshold: int = 75):
        genai.configure(api_key=google_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.pass_threshold = pass_threshold
        logger.info(f"QuestionnaireJudge initialized with pass threshold: {pass_threshold}")
    
    def judge_questionnaire(
        self,
        questionnaire: QuestionnaireOutput,
        input_data: QuestionnaireInput,
        rag_questions: List[RetrievalResult]
    ) -> Dict[str, Any]:
        try:
            logger.info(f"🧑‍⚖️ Judging questionnaire: {questionnaire.title}")
            
            prompt = self._build_judge_prompt(questionnaire, input_data, rag_questions)
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temperature for consistent evaluation
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "score": {"type": "number"},
                            "relevance_score": {"type": "number"},
                            "completeness_score": {"type": "number"},
                            "quality_score": {"type": "number"},
                            "diversity_score": {"type": "number"},
                            "feedback": {"type": "string"},
                            "strengths": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "improvements": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["score", "feedback"]
                    }
                )
            )
            
            result = eval(response.text)
            score = float(result.get("score", 0))
            status = "PASS" if score >= self.pass_threshold else "FAIL"
            
            logger.info(f"{'✅' if status == 'PASS' else '❌'} Judge result: {score}/100 - {status}")
            
            return {
                "status": status,
                "score": score,
                "feedback": result.get("feedback", ""),
                "breakdown": {
                    "relevance": result.get("relevance_score", 0),
                    "completeness": result.get("completeness_score", 0),
                    "quality": result.get("quality_score", 0),
                    "diversity": result.get("diversity_score", 0)
                },
                "strengths": result.get("strengths", []),
                "improvements": result.get("improvements", [])
            }
            
        except Exception as e:
            logger.error(f"Error in judge evaluation: {str(e)}")
            return {
                "status": "ERROR",
                "score": 0,
                "feedback": f"Judge evaluation failed: {str(e)}",
                "breakdown": {},
                "strengths": [],
                "improvements": []
            }
    
    def _build_judge_prompt(
        self,
        questionnaire: QuestionnaireOutput,
        input_data: QuestionnaireInput,
        rag_questions: List[RetrievalResult]
    ) -> str:
        
        # Format questions by section
        questions_by_section = {}
        for q in questionnaire.questions:
            if q.section not in questions_by_section:
                questions_by_section[q.section] = []
            questions_by_section[q.section].append(q.question_text)
        
        questions_text = ""
        for section, questions in questions_by_section.items():
            questions_text += f"\n**{section}:**\n"
            for i, q in enumerate(questions, 1):
                questions_text += f"  {i}. {q}\n"
        
        # Format RAG reference questions
        rag_text = ""
        if rag_questions:
            rag_text = "\n**Retrieved Reference Questions (for context):**\n"
            for i, ref in enumerate(rag_questions[:5], 1):  # Limit to top 5
                rag_text += f"  {i}. [{ref.section}] {ref.question}\n"
        
        prompt = f"""You are an expert **Solution Architecture Consultant** evaluating the quality of a questionnaire designed to gather requirements for a cloud project.

**EVALUATION RUBRIC (100 points total):**

**1. RELEVANCE TO REQUIREMENTS (30 points)**
- Do questions directly address the customer's stated requirements and business domain?
- Are questions tailored to the specific project type, timeline, and budget?
- Do questions avoid generic or irrelevant content?

**2. COMPLETENESS (25 points)**
- Do questions cover all 4 key criteria:
  * Business Problems & Objectives
  * Current Environment / As-Is Architecture
  * To-be Architecture (Functional & Non-Functional Requirements)
  * Timeline & Budget
- Are there any critical gaps in the questionnaire?
- Is the question count within the expected range ({input_data.language} language)?

**3. QUESTION QUALITY (25 points)**
- Are questions clear, specific, and actionable?
- Do they use professional, consultative tone?
- Do they include helpful examples or clarifications where needed?
- Are they open-ended to encourage detailed responses?
- Do they avoid yes/no questions unless strategically necessary?

**4. DIVERSITY & STRUCTURE (20 points)**
- Are questions organized into logical sections (4-6 sections recommended)?
- Do questions within each section relate coherently?
- Is there good variety in question types (strategic, technical, operational)?
- Are questions NOT just rephrased versions of the reference questions?

---

**ORIGINAL REQUIREMENTS:**
- Customer: {input_data.customer_name}
- Business Domain: {input_data.business_domain}
- Project Type: {input_data.project_type or 'Not specified'}
- Requirements: {input_data.requirements}
- Audience: {input_data.audience}
- Timeline: {input_data.timeline or 'Not specified'}
- Budget: {input_data.budget_range or 'Not specified'}
- Additional Context: {input_data.additional_context or 'None'}

---

**GENERATED QUESTIONNAIRE:**
Title: {questionnaire.title}
Description: {questionnaire.description}
Total Questions: {questionnaire.total_questions}
Language: {questionnaire.language}

{questions_text}

{rag_text}

---

**YOUR TASK:**
1. Evaluate the questionnaire against the rubric above
2. Assign scores for each criterion (relevance, completeness, quality, diversity)
3. Calculate total score (0-100)
4. Provide specific, actionable feedback
5. List key strengths and areas for improvement

**OUTPUT FORMAT (JSON):**
{{
    "score": <total score 0-100>,
    "relevance_score": <0-30>,
    "completeness_score": <0-25>,
    "quality_score": <0-25>,
    "diversity_score": <0-20>,
    "feedback": "Detailed explanation of the evaluation with specific examples",
    "strengths": ["strength 1", "strength 2", ...],
    "improvements": ["improvement 1", "improvement 2", ...]
}}"""
        
        return prompt


# Standalone test function
def test_judge():
    import os
    from dotenv import load_dotenv
    from datetime import datetime
    from .model import Question
    
    load_dotenv()
    
    # Sample data
    input_data = QuestionnaireInput(
        customer_name="Test Corp",
        requirements="Build a data analytics platform",
        business_domain="IT and Software Services",
        audience="Data Team",
        language="English",
        project_type="Data Analytics"
    )
    
    sample_questions = [
        Question(id="q1", section="Business Objectives", question_text="What are your main business goals?"),
        Question(id="q2", section="Business Objectives", question_text="What KPIs do you want to track?"),
        Question(id="q3", section="Current State", question_text="What data sources do you currently use?"),
        Question(id="q4", section="Technical Requirements", question_text="What are your scalability needs?"),
    ]
    
    questionnaire = QuestionnaireOutput(
        questionnaire_id="test-123",
        title="Data Analytics Requirements",
        description="Questionnaire for data platform project",
        customer_name="Test Corp",
        business_domain="IT and Software Services",
        audience="Data Team",
        language="English",
        questions=sample_questions,
        created_at=datetime.now(),
        total_questions=len(sample_questions)
    )
    
    judge = QuestionnaireJudge(google_api_key=os.getenv('GOOGLE_API_KEY'))
    result = judge.judge_questionnaire(questionnaire, input_data, [])
    
    print(f"\n{'='*60}")
    print(f"JUDGE RESULT: {result['status']} - Score: {result['score']}/100")
    print(f"{'='*60}")
    print(f"\nFeedback: {result['feedback']}")
    print(f"\nBreakdown:")
    for key, value in result['breakdown'].items():
        print(f"  {key}: {value}")
    print(f"\nStrengths:")
    for s in result['strengths']:
        print(f"  ✅ {s}")
    print(f"\nImprovements:")
    for i in result['improvements']:
        print(f"  ⚠️ {i}")


if __name__ == "__main__":
    test_judge()
