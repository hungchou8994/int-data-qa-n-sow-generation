

import os
import json
import logging
from typing import Optional, Dict, Any, List

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

from .model import (
    ProjectDetail,
    ProjectAssumption,
    ScopeOfWork,
    ClientInformation,
    QuestionnaireAnswer,
    JudgeResult
)

logger = logging.getLogger(__name__)


# ===================== JUDGE RUBRICS =====================

PROJECT_DETAIL_RUBRIC = """
You are a **Senior QA Expert** evaluating the quality of a **Project Detail** document.

### EVALUATION CRITERIA (Total: 100 points)

**1. Accuracy & Alignment with Input (40 points)**
- Does the overview accurately reflect client requirements and questionnaire answers?
- Are key features aligned with the business domain and project type?
- Is there any contradiction with input data?

**2. Completeness & Detail (30 points)**
- Does it cover all major aspects mentioned in requirements?
- Are key features sufficiently detailed (3-5 bullet points each)?
- Are there any critical missing features based on the questionnaire?

**3. Specificity & Clarity (20 points)**
- Are features specific and concrete (not generic/vague)?
- Are technical details clear and well-explained?
- Is the language professional and precise?

**4. Structure & Format (10 points)**
- Does it follow the required format (overview + numbered features)?
- Are features properly organized and categorized?
- Is the document well-structured and easy to read?



### OUTPUT FORMAT (JSON):
(Note: The exact JSON structure is defined in the API; this is an explanation of each field.)
-**score**: 0-100
-**status**: "PASS" or "FAIL"
-**feedback**: Overall assessment of the Project Detail
-**issues**: List of specific issues found
-**strengths**: List of specific strengths observed



**IMPORTANT**: Be strict but fair. Focus on SPECIFICITY and ALIGNMENT with input data.
"""


PROJECT_ASSUMPTION_RUBRIC = """
You are a **Senior QA Expert** evaluating the quality of a **Project Assumption** document.

### EVALUATION CRITERIA (Total: 100 points)

**1. Consistency with Project Detail (35 points)**
- Are assumptions logically consistent with the Project Detail?
- Do they align with the scope and features defined?
- Are there any contradictions (e.g., PD mentions feature X but PA excludes it)?

**2. Completeness of Sections (25 points)**
- Does it include "Data Scope" section?
- Does it include "SoW" section?
- Does it include domain-specific sections (e.g., "Forecasting", "Automation")?

**3. Specificity & Measurability (25 points)**
- Are assumptions specific with numbers/metrics (e.g., "Up to 1000 SKUs", "80% accuracy")?
- Are they measurable and verifiable?
- Are they realistic and achievable?

**4. Clarity & Professional Quality (15 points)**
- Are assumptions clearly stated?
- Is the language professional?
- Is the structure well-organized?

### OUTPUT FORMAT (JSON):
(Note: The exact JSON structure is defined in the API; this is an explanation of each field.)
-**score**: 0-100
-**status**: "PASS" or "FAIL"
-**feedback**: Overall assessment of the Project Assumption
-**issues**: List of specific issues found
-**strengths**: List of specific strengths observed




**CRITICAL**: Check for consistency with Project Detail. Any contradiction = FAIL.
"""


SCOPE_OF_WORK_RUBRIC = """
You are a **Senior QA Expert** evaluating the quality of a **Scope of Work** (task breakdown) document.

### EVALUATION CRITERIA (Total: 100 points)

**1. Consistency with Project Assumption (30 points)**
- Do tasks align with assumptions (e.g., if PA says "MVP only", no production tasks)?
- Are man-days realistic given PA constraints?
- Are there any contradictions with PA scope?

**2. Coverage of RAG Tasks (25 points)**
- Are relevant tasks from RAG properly incorporated?
- Are RAG tasks adapted to this specific project context?
- Is there good balance between RAG tasks and custom tasks?

**3. Completeness & Detail (25 points)**
- Are all necessary task categories covered?
- Is each task's content sufficiently detailed?
- Are there any obvious missing tasks based on PD and PA?

**4. Specificity & Realism (20 points)**
- Are task contents specific and actionable (not vague)?
- Are individual task man-day estimates reasonable?
- Are task titles clear and descriptive?

### OUTPUT FORMAT (JSON):
(Note: The exact JSON structure is defined in the API; this is an explanation of each field.)
-**score**: 0-100
-**status**: "PASS" or "FAIL"
-**feedback**: Overall assessment of the Scope of Work
-**issues**: List of specific issues found
-**strengths**: List of specific strengths observed


**CRITICAL**: Check consistency with PA. Any contradiction or scope mismatch = FAIL.
"""


class SOWJudge:
    
    def __init__(self, google_api_key: Optional[str] = None, pass_threshold: int = 75):
        """
        Initialize judge with API key
        
        Args:
            google_api_key: Google API key for Gemini
            pass_threshold: Minimum score (0-100) for PASS status (default 75)
        """
        self.api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key is required")
        
        self.pass_threshold = pass_threshold
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info(f"SOWJudge initialized (pass_threshold={pass_threshold})")
    
    def judge_project_detail(
        self,
        project_detail: ProjectDetail,
        client_info: ClientInformation,
        questionnaire_answers: List[QuestionnaireAnswer]
    ) -> JudgeResult:
        try:
            logger.info(f" Judging Project Detail for {client_info.customer_name}")
            
            # Build context
            context = self._build_detail_context(
                project_detail, client_info, questionnaire_answers
            )
            
            # Create prompt
            prompt = f"{PROJECT_DETAIL_RUBRIC}\n\n{context}\n\nPlease evaluate this Project Detail and provide your assessment in JSON format."
            
            # Generate evaluation
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,  
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "score": {"type": "number"},
                            "status": {"type": "string"},
                            "feedback": {"type": "string"},
                            "issues": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "strengths": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                        },
                        "required": ["score", "status", "feedback", "issues"]
                    }
                )
            )
            
            # Parse response
            result = json.loads(response.text)
            
            # Determine status based on score and threshold
            score = float(result.get("score", 0))
            status = "PASS" if score >= self.pass_threshold else "FAIL"
            
            judge_result = JudgeResult(
                component="project_detail",
                status=status,
                score=score,
                feedback=result.get("feedback", ""),
                issues=result.get("issues", []),
            )
            
            logger.info(f"✅ Judge Result: {judge_result.status} (Score: {judge_result.score}/100, Threshold: {self.pass_threshold})")
            return judge_result
            
        except Exception as e:
            logger.error(f"Error judging project detail: {str(e)}")
            # Return FAIL on error
            return JudgeResult(
                component="project_detail",
                status="FAIL",
                score=0,
                feedback=f"Error during evaluation: {str(e)}",
                issues=["Evaluation failed due to technical error"],
            )
    
    def judge_project_assumption(
        self,
        project_assumption: ProjectAssumption,
        project_detail: ProjectDetail,
        client_info: ClientInformation,
        questionnaire_answers: List[QuestionnaireAnswer]
    ) -> JudgeResult:
        try:
            logger.info(f" Judging Project Assumption for {client_info.customer_name}")
            
            # Build context
            context = self._build_assumption_context(
                project_assumption, project_detail, client_info, questionnaire_answers
            )
            
            # Create prompt
            prompt = f"{PROJECT_ASSUMPTION_RUBRIC}\n\n{context}\n\nPlease evaluate this Project Assumption and provide your assessment in JSON format."
            
            # Generate evaluation
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "score": {"type": "number"},
                            "status": {"type": "string"},
                            "feedback": {"type": "string"},
                            "issues": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "strengths": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                        },
                    }
                )
            )
            
            # Parse response
            result = json.loads(response.text)
            
            # Determine status based on score and threshold
            score = float(result.get("score", 0))
            status = "PASS" if score >= self.pass_threshold else "FAIL"
            
            judge_result = JudgeResult(
                component="project_assumption",
                status=status,
                score=score,
                feedback=result.get("feedback", ""),
                issues=result.get("issues", []),
            )
            
            logger.info(f"✅ Judge Result: {judge_result.status} (Score: {judge_result.score}/100, Threshold: {self.pass_threshold})")
            return judge_result
            
        except Exception as e:
            logger.error(f" Error judging project assumption: {str(e)}")
            return JudgeResult(
                component="project_assumption",
                status="FAIL",
                score=0,
                feedback=f"Error during evaluation: {str(e)}",
                issues=["Evaluation failed due to technical error"],
            )
    
    def judge_scope_of_work(
        self,
        scope_of_work: ScopeOfWork,
        project_assumption: ProjectAssumption,
        project_detail: ProjectDetail,
        rag_tasks: List[Dict[str, Any]]
    ) -> JudgeResult:
        """Evaluate Scope of Work quality"""
        try:
            logger.info(f" Judging Scope of Work for {scope_of_work.customer_name}")
            
            # Build context
            context = self._build_sow_context(
                scope_of_work, project_assumption, project_detail, rag_tasks
            )
            
            # Create prompt
            prompt = f"{SCOPE_OF_WORK_RUBRIC}\n\n{context}\n\nPlease evaluate this Scope of Work and provide your assessment in JSON format."
            
            # Generate evaluation
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "properties": {
                            "score": {"type": "number"},
                            "status": {"type": "string"},
                            "feedback": {"type": "string"},
                            "issues": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "strengths": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
                )
            )

            # Parse response
            result = json.loads(response.text)
            
            # Determine status based on score and threshold
            score = float(result.get("score", 0))
            status = "PASS" if score >= self.pass_threshold else "FAIL"
            
            judge_result = JudgeResult(
                component="scope_of_work",
                status=status,
                score=score,
                feedback=result.get("feedback", ""),
                issues=result.get("issues", []),
            )
            
            logger.info(f"✅ Judge Result: {judge_result.status} (Score: {judge_result.score}/100, Threshold: {self.pass_threshold})")
            return judge_result
            
        except Exception as e:
            logger.error(f" Error judging scope of work: {str(e)}")
            return JudgeResult(
                component="scope_of_work",
                status="FAIL",
                score=0,
                feedback=f"Error during evaluation: {str(e)}",
                issues=["Evaluation failed due to technical error"],
            )
    
    # =============== CONTEXT BUILDERS ===============
    
    def _build_detail_context(
        self,
        detail: ProjectDetail,
        client_info: ClientInformation,
        answers: List[QuestionnaireAnswer]
    ) -> str:
        """Build context for detail evaluation"""
        parts = ["=== INPUT DATA ==="]
        parts.append(f"Customer: {client_info.customer_name}")
        parts.append(f"Business Domain: {client_info.business_domain}")
        parts.append(f"Requirements: {client_info.requirements}")
        parts.append(f"Project Type: {client_info.project_type}")
        
        parts.append("\n=== QUESTIONNAIRE ANSWERS ===")
        for ans in answers:  # Limit to avoid token overflow
            parts.append(f"Q: {ans.question_text}")
            parts.append(f"A: {ans.answer}")
        
        parts.append("\n=== PROJECT DETAIL TO EVALUATE ===")
        parts.append(f"Overview: {detail.overview}")
        parts.append(f"\nKey Features ({len(detail.key_features)} total):")
        for feature in detail.key_features:
            parts.append(feature)
        
        return "\n".join(parts)
    
    def _build_assumption_context(
        self,
        assumption: ProjectAssumption,
        detail: ProjectDetail,
        client_info: ClientInformation,
        answers: List[QuestionnaireAnswer]
    ) -> str:
        """Build context for assumption evaluation"""
        parts = ["=== PROJECT DETAIL (Reference) ==="]
        parts.append(f"Overview: {detail.overview}")
        parts.append(f"Key Features: {len(detail.key_features)} features defined")
        
        parts.append("\n=== PROJECT ASSUMPTION TO EVALUATE ===")
        for section in assumption.assumptions:
            parts.append(f"\n{section.section}:")
            for point in section.points:
                parts.append(f"  - {point}")
        
        return "\n".join(parts)
    
    def _build_sow_context(
        self,
        sow: ScopeOfWork,
        assumption: ProjectAssumption,
        detail: ProjectDetail,
        rag_tasks: List[Dict[str, Any]]
    ) -> str:
        """Build context for SoW evaluation"""
        parts = ["=== PROJECT ASSUMPTION (Reference) ==="]
        for section in assumption.assumptions:
            parts.append(f"{section.section}:")
            for point in section.points:  
                parts.append(f"  - {point}")
        
        parts.append(f"\n=== RAG TASKS ({len(rag_tasks)} retrieved) ===")
        for task in rag_tasks:
            parts.append(f"- [{task['task_category']}] {task['task_title']} ({task['man_days']} days)")
        
        parts.append(f"\n=== SCOPE OF WORK TO EVALUATE ===")
        parts.append(f"Total Tasks: {sow.total_tasks}")
        parts.append(f"Total Man-Days: {sow.total_man_days}")
        
        grouped = sow.get_tasks_by_category()
        for category, tasks in grouped.items():
            parts.append(f"\n{category} ({len(tasks)} tasks):")
            for task in tasks:
                parts.append(f"  - {task.task_title} ({task.man_days} days) [{task.source}]")
                parts.append(f"    {task.content}...")
        
        return "\n".join(parts)
