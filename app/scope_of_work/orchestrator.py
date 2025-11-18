"""
SOW Orchestrator - Manages Auto-Correction Loop and Cascade Regeneration
Implements PHASE 1 (Auto-Correction) and PHASE 3 (Cascade Regeneration with Feedback)
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import sys
from pathlib import Path

# Add parent directory to path for rag imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from .model import (
    ClientInformation,
    QuestionnaireAnswer,
    ProjectDetail,
    ProjectDetailInput,
    ProjectAssumption,
    ProjectAssumptionInput,
    ScopeOfWork,
    ScopeOfWorkInput,
    GenerationConfig,
    JudgeResult,
    ComponentVersion
)
from .engine import SOWEngine
from .judge import SOWJudge

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    """Result from orchestration process"""
    status: str  # "success", "partial_failure", "failure"
    project_detail: Optional[ProjectDetail]
    project_assumption: Optional[ProjectAssumption]
    scope_of_work: Optional[ScopeOfWork]
    
    # Judge results for each component
    detail_judge: Optional[JudgeResult]
    assumption_judge: Optional[JudgeResult]
    sow_judge: Optional[JudgeResult]
    
    # Error information
    failed_component: Optional[str]  # "project_detail", "project_assumption", "scope_of_work"
    error_message: Optional[str]
    
    # Version tracking
    detail_version: str
    assumption_version: str
    sow_version: str


class SOWOrchestrator:
    """
    Orchestrates the entire SOW generation workflow:
    - PHASE 1: Auto-correction loop (generate -> judge -> regenerate)
    - PHASE 3: Cascade regeneration based on human feedback
    """
    
    def __init__(
        self,
        google_api_key: Optional[str] = None,
        max_auto_retries: int = 3,
        pass_threshold: int = 75,
        top_k: int = 20
    ):
        """
        Initialize orchestrator
        
        Args:
            google_api_key: Google API key for LLM and Judge
            max_auto_retries: Maximum retry attempts for auto-correction loop
            pass_threshold: Minimum judge score (0-100) for PASS status
            top_k: Number of similar tasks to retrieve from RAG for SoW generation
        """
        self.engine = SOWEngine(google_api_key)
        self.judge = SOWJudge(google_api_key, pass_threshold=pass_threshold)
        self.max_auto_retries = max_auto_retries
        self.pass_threshold = pass_threshold
        self.top_k = top_k
        
        # History tracking
        self.detail_history: List[ComponentVersion] = []
        self.assumption_history: List[ComponentVersion] = []
        self.sow_history: List[ComponentVersion] = []
        
        logger.info(f"SOWOrchestrator initialized (max_auto_retries={max_auto_retries}, pass_threshold={pass_threshold}, top_k={top_k})")
    
    def generate_complete_sow(
        self,
        client_info: ClientInformation,
        questionnaire_answers: List[QuestionnaireAnswer],
        config: Optional[GenerationConfig] = None
    ) -> OrchestrationResult:
        """
        PHASE 1: Auto-Correction Loop
        
        Generates all 3 components with automatic quality control:
        1. Generate Project Detail -> Judge -> Regenerate if FAIL (max 3 times)
        2. Generate Project Assumption -> Judge -> Regenerate if FAIL (max 3 times)
        3. Generate Scope of Work -> Judge -> Regenerate if FAIL (max 3 times)
        
        Returns result with status indicating success or which component failed
        """
        logger.info("=" * 60)
        logger.info(" PHASE 1: AUTO-CORRECTION LOOP STARTED")
        logger.info("=" * 60)
        
        if config is None:
            config = GenerationConfig()
        
        # Step 1: Generate and validate Project Detail
        logger.info("\nSTEP 1: Generating Project Detail...")
        detail_result = self._generate_with_validation(
            component_type="project_detail",
            client_info=client_info,
            questionnaire_answers=questionnaire_answers,
            config=config
        )
        
        if not detail_result['success']:
            logger.error(" Project Detail generation failed after max retries")
            return OrchestrationResult(
                status="failure",
                project_detail=detail_result.get('content'),
                project_assumption=None,
                scope_of_work=None,
                detail_judge=detail_result.get('judge_result'),
                assumption_judge=None,
                sow_judge=None,
                failed_component="project_detail",
                error_message=detail_result.get('error'),
                detail_version="v_failed",
                assumption_version="",
                sow_version=""
            )
        
        project_detail = detail_result['content']
        detail_judge = detail_result['judge_result']
        logger.info(f" Project Detail PASSED (Score: {detail_judge.score}/100)")
        
        # Save to history
        self.detail_history.append(ComponentVersion(
            component="project_detail",
            version="v_final_auto",
            content=project_detail,
            judge_result=detail_judge,
            created_at=datetime.now(),
            created_by="auto"
        ))
        
        # Step 2: Generate and validate Project Assumption
        logger.info("\n STEP 2: Generating Project Assumption...")
        assumption_result = self._generate_with_validation(
            component_type="project_assumption",
            client_info=client_info,
            questionnaire_answers=questionnaire_answers,
            project_detail=project_detail,
            config=config
        )
        
        if not assumption_result['success']:
            logger.error(" Project Assumption generation failed after max retries")
            return OrchestrationResult(
                status="partial_failure",
                project_detail=project_detail,
                project_assumption=assumption_result.get('content'),
                scope_of_work=None,
                detail_judge=detail_judge,
                assumption_judge=assumption_result.get('judge_result'),
                sow_judge=None,
                failed_component="project_assumption",
                error_message=assumption_result.get('error'),
                detail_version="v_final_auto",
                assumption_version="v_failed",
                sow_version=""
            )
        
        project_assumption = assumption_result['content']
        assumption_judge = assumption_result['judge_result']
        logger.info(f" Project Assumption PASSED (Score: {assumption_judge.score}/100)")
        
        # Save to history
        self.assumption_history.append(ComponentVersion(
            component="project_assumption",
            version="v_final_auto",
            content=project_assumption,
            judge_result=assumption_judge,
            created_at=datetime.now(),
            created_by="auto"
        ))
        
        # Step 3: Generate and validate Scope of Work
        logger.info("\n STEP 3: Generating Scope of Work (with RAG)...")
        sow_result = self._generate_with_validation(
            component_type="scope_of_work",
            client_info=client_info,
            questionnaire_answers=questionnaire_answers,
            project_detail=project_detail,
            project_assumption=project_assumption,
            config=config
        )
        
        if not sow_result['success']:
            logger.error(" Scope of Work generation failed after max retries")
            return OrchestrationResult(
                status="partial_failure",
                project_detail=project_detail,
                project_assumption=project_assumption,
                scope_of_work=sow_result.get('content'),
                detail_judge=detail_judge,
                assumption_judge=assumption_judge,
                sow_judge=sow_result.get('judge_result'),
                failed_component="scope_of_work",
                error_message=sow_result.get('error'),
                detail_version="v_final_auto",
                assumption_version="v_final_auto",
                sow_version="v_failed"
            )
        
        scope_of_work = sow_result['content']
        sow_judge = sow_result['judge_result']
        logger.info(f" Scope of Work PASSED (Score: {sow_judge.score}/100)")
        
        # Save to history
        self.sow_history.append(ComponentVersion(
            component="scope_of_work",
            version="v_final_auto",
            content=scope_of_work,
            judge_result=sow_judge,
            created_at=datetime.now(),
            created_by="auto"
        ))
        
        logger.info("\n" + "=" * 60)
        logger.info(" PHASE 1 COMPLETED SUCCESSFULLY")
        logger.info(f"   Project Detail: {detail_judge.score}/100")
        logger.info(f"   Project Assumption: {assumption_judge.score}/100")
        logger.info(f"   Scope of Work: {sow_judge.score}/100 ({scope_of_work.total_tasks} tasks, {scope_of_work.total_man_days} days)")
        logger.info("=" * 60)
        
        return OrchestrationResult(
            status="success",
            project_detail=project_detail,
            project_assumption=project_assumption,
            scope_of_work=scope_of_work,
            detail_judge=detail_judge,
            assumption_judge=assumption_judge,
            sow_judge=sow_judge,
            failed_component=None,
            error_message=None,
            detail_version="v_final_auto",
            assumption_version="v_final_auto",
            sow_version="v_final_auto"
        )
    
    def handle_feedback(
        self,
        target_component: str,  # "project_detail", "project_assumption", "scope_of_work"
        feedback: str,
        current_detail: ProjectDetail,
        current_assumption: ProjectAssumption,
        current_sow: ScopeOfWork,
        client_info: ClientInformation,
        questionnaire_answers: List[QuestionnaireAnswer],
        config: Optional[GenerationConfig] = None
    ) -> OrchestrationResult:
        """
        PHASE 3: Cascade Regeneration with Human Feedback
        
        Logic:
        - If target == "project_detail": Regen PD -> Regen PA -> Regen SoW (full cascade)
        - If target == "project_assumption": Keep PD -> Regen PA -> Regen SoW
        - If target == "scope_of_work": Keep PD, PA -> Regen SoW only
        
        Each regenerated component is validated by Judge
        """
        logger.info("=" * 60)
        logger.info(f" PHASE 3: CASCADE REGENERATION (Target: {target_component})")
        logger.info(f" Feedback: {feedback[:100]}...")
        logger.info("=" * 60)
        
        if config is None:
            config = GenerationConfig()
        
        # Determine version number
        version_num = len([v for v in self.detail_history if v.created_by == "human_feedback"]) + 1
        version_suffix = f"v_human_{version_num}"
        
        # CASE 1: Project Detail changed (Full Cascade)
        if target_component == "project_detail":
            logger.info(" Target: Project Detail -> Full cascade required")
            
            # Regen PD
            logger.info("\n Step 1: Regenerating Project Detail...")
            detail_result = self._regenerate_component(
                component_type="project_detail",
                feedback=feedback,
                previous_content=current_detail,
                client_info=client_info,
                questionnaire_answers=questionnaire_answers,
                config=config
            )
            
            if not detail_result['success']:
                return self._create_failure_result(
                    "project_detail", detail_result, 
                    current_detail, current_assumption, current_sow,
                    version_suffix
                )
            
            new_detail = detail_result['content']
            detail_judge = detail_result['judge_result']
            self.detail_history.append(ComponentVersion(
                component="project_detail", version=version_suffix,
                content=new_detail, judge_result=detail_judge,
                created_at=datetime.now(), created_by="human_feedback"
            ))
            
            # CASCADE: Regen PA (using new PD)
            logger.info("\n Step 2: Cascading to Project Assumption...")
            assumption_result = self._generate_with_validation(
                component_type="project_assumption",
                client_info=client_info,
                questionnaire_answers=questionnaire_answers,
                project_detail=new_detail,
                config=config
            )
            
            if not assumption_result['success']:
                return self._create_failure_result(
                    "project_assumption", assumption_result,
                    new_detail, current_assumption, current_sow,
                    version_suffix
                )
            
            new_assumption = assumption_result['content']
            assumption_judge = assumption_result['judge_result']
            self.assumption_history.append(ComponentVersion(
                component="project_assumption", version=version_suffix,
                content=new_assumption, judge_result=assumption_judge,
                created_at=datetime.now(), created_by="human_feedback"
            ))
            
            # CASCADE: Regen SoW (using new PD + new PA)
            logger.info("\n Step 3: Cascading to Scope of Work...")
            sow_result = self._generate_with_validation(
                component_type="scope_of_work",
                client_info=client_info,
                questionnaire_answers=questionnaire_answers,
                project_detail=new_detail,
                project_assumption=new_assumption,
                config=config
            )
            
            if not sow_result['success']:
                return self._create_failure_result(
                    "scope_of_work", sow_result,
                    new_detail, new_assumption, current_sow,
                    version_suffix
                )
            
            new_sow = sow_result['content']
            sow_judge = sow_result['judge_result']
            self.sow_history.append(ComponentVersion(
                component="scope_of_work", version=version_suffix,
                content=new_sow, judge_result=sow_judge,
                created_at=datetime.now(), created_by="human_feedback"
            ))
            
            logger.info("Full cascade completed successfully")
            return OrchestrationResult(
                status="success",
                project_detail=new_detail,
                project_assumption=new_assumption,
                scope_of_work=new_sow,
                detail_judge=detail_judge,
                assumption_judge=assumption_judge,
                sow_judge=sow_judge,
                failed_component=None,
                error_message=None,
                detail_version=version_suffix,
                assumption_version=version_suffix,
                sow_version=version_suffix
            )
        
        # CASE 2: Project Assumption changed (PA + SoW cascade)
        elif target_component == "project_assumption":
            logger.info(" Target: Project Assumption -> Cascade to SoW")
            
            # Regen PA (using existing PD)
            logger.info("\nStep 1: Regenerating Project Assumption...")
            assumption_result = self._regenerate_component(
                component_type="project_assumption",
                feedback=feedback,
                previous_content=current_assumption,
                client_info=client_info,
                questionnaire_answers=questionnaire_answers,
                project_detail=current_detail,
                config=config
            )
            
            if not assumption_result['success']:
                return self._create_failure_result(
                    "project_assumption", assumption_result,
                    current_detail, current_assumption, current_sow,
                    version_suffix
                )
            
            new_assumption = assumption_result['content']
            assumption_judge = assumption_result['judge_result']
            self.assumption_history.append(ComponentVersion(
                component="project_assumption", version=version_suffix,
                content=new_assumption, judge_result=assumption_judge,
                created_at=datetime.now(), created_by="human_feedback"
            ))
            
            # CASCADE: Regen SoW (using existing PD + new PA)
            logger.info("\n📝 Step 2: Cascading to Scope of Work...")
            sow_result = self._generate_with_validation(
                component_type="scope_of_work",
                client_info=client_info,
                questionnaire_answers=questionnaire_answers,
                project_detail=current_detail,
                project_assumption=new_assumption,
                config=config
            )
            
            if not sow_result['success']:
                return self._create_failure_result(
                    "scope_of_work", sow_result,
                    current_detail, new_assumption, current_sow,
                    version_suffix
                )
            
            new_sow = sow_result['content']
            sow_judge = sow_result['judge_result']
            self.sow_history.append(ComponentVersion(
                component="scope_of_work", version=version_suffix,
                content=new_sow, judge_result=sow_judge,
                created_at=datetime.now(), created_by="human_feedback"
            ))
            
            logger.info(" Cascade to SoW completed successfully")
            return OrchestrationResult(
                status="success",
                project_detail=current_detail,  # Keep existing
                project_assumption=new_assumption,
                scope_of_work=new_sow,
                detail_judge=self.detail_history[-1].judge_result,
                assumption_judge=assumption_judge,
                sow_judge=sow_judge,
                failed_component=None,
                error_message=None,
                detail_version=self.detail_history[-1].version,
                assumption_version=version_suffix,
                sow_version=version_suffix
            )
        
        # CASE 3: Scope of Work changed (No cascade)
        elif target_component == "scope_of_work":
            logger.info("🔄 Target: Scope of Work -> No cascade needed")
            
            # Regen SoW only (using existing PD + PA)
            logger.info("\n📝 Step 1: Regenerating Scope of Work...")
            sow_result = self._regenerate_component(
                component_type="scope_of_work",
                feedback=feedback,
                previous_content=current_sow,
                client_info=client_info,
                questionnaire_answers=questionnaire_answers,
                project_detail=current_detail,
                project_assumption=current_assumption,
                config=config
            )
            
            if not sow_result['success']:
                return self._create_failure_result(
                    "scope_of_work", sow_result,
                    current_detail, current_assumption, current_sow,
                    version_suffix
                )
            
            new_sow = sow_result['content']
            sow_judge = sow_result['judge_result']
            self.sow_history.append(ComponentVersion(
                component="scope_of_work", version=version_suffix,
                content=new_sow, judge_result=sow_judge,
                created_at=datetime.now(), created_by="human_feedback"
            ))
            
            logger.info("✅ SoW regeneration completed successfully")
            return OrchestrationResult(
                status="success",
                project_detail=current_detail,  # Keep existing
                project_assumption=current_assumption,  # Keep existing
                scope_of_work=new_sow,
                detail_judge=self.detail_history[-1].judge_result,
                assumption_judge=self.assumption_history[-1].judge_result,
                sow_judge=sow_judge,
                failed_component=None,
                error_message=None,
                detail_version=self.detail_history[-1].version,
                assumption_version=self.assumption_history[-1].version,
                sow_version=version_suffix
            )
        
        else:
            raise ValueError(f"Invalid target_component: {target_component}")
    
    # =============== HELPER METHODS ===============
    
    def _generate_with_validation(
        self,
        component_type: str,
        client_info: ClientInformation,
        questionnaire_answers: List[QuestionnaireAnswer],
        config: GenerationConfig,
        project_detail: Optional[ProjectDetail] = None,
        project_assumption: Optional[ProjectAssumption] = None
    ) -> Dict[str, Any]:
        """
        Generate component and validate with judge (auto-retry loop)
        Returns: {'success': bool, 'content': component, 'judge_result': JudgeResult, 'error': str}
        """
        for attempt in range(self.max_auto_retries):
            try:
                logger.info(f"🔄 Attempt {attempt + 1}/{self.max_auto_retries}")
                
                # Generate component
                if component_type == "project_detail":
                    input_data = ProjectDetailInput(client_info, questionnaire_answers)
                    content = self.engine.generate_project_detail(input_data, config)
                    judge_result = self.judge.judge_project_detail(
                        content, client_info, questionnaire_answers
                    )
                
                elif component_type == "project_assumption":
                    input_data = ProjectAssumptionInput(
                        client_info, questionnaire_answers, project_detail
                    )
                    content = self.engine.generate_project_assumption(input_data, config)
                    judge_result = self.judge.judge_project_assumption(
                        content, project_detail, client_info, questionnaire_answers
                    )
                
                elif component_type == "scope_of_work":
                    input_data = ScopeOfWorkInput(
                        client_info, questionnaire_answers, project_detail, project_assumption
                    )
                    # Engine returns (ScopeOfWork, rag_tasks) to avoid duplicate RAG calls
                    content, rag_tasks = self.engine.generate_scope_of_work(
                        input_data, config, top_k=self.top_k
                    )
                    
                    # Use rag_tasks from engine (no need to retrieve again)
                    judge_result = self.judge.judge_scope_of_work(
                        content, project_assumption, project_detail, rag_tasks
                    )
                
                else:
                    raise ValueError(f"Unknown component type: {component_type}")
                
                # Check judge result
                if judge_result.status == "PASS":
                    logger.info(f"PASS (Score: {judge_result.score}/100)")
                    return {
                        'success': True,
                        'content': content,
                        'judge_result': judge_result,
                        'error': None
                    }
                else:
                    logger.warning(f"FAIL (Score: {judge_result.score}/100)")
                    logger.warning(f"Issues: {', '.join(judge_result.issues)}")
                    
                    if attempt < self.max_auto_retries - 1:
                        logger.info("🔄 Regenerating with judge feedback...")
                        # Continue loop with regeneration
                    else:
                        logger.error(" Max retries reached")
                        return {
                            'success': False,
                            'content': content,
                            'judge_result': judge_result,
                            'error': f"Failed validation after {self.max_auto_retries} attempts. Last score: {judge_result.score}/100"
                        }
            
            except Exception as e:
                logger.error(f" Error in attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_auto_retries - 1:
                    return {
                        'success': False,
                        'content': None,
                        'judge_result': None,
                        'error': str(e)
                    }
        
        return {
            'success': False,
            'content': None,
            'judge_result': None,
            'error': "Max retries exceeded"
        }
    
    def _regenerate_component(
        self,
        component_type: str,
        feedback: str,
        previous_content: Any,
        client_info: ClientInformation,
        questionnaire_answers: List[QuestionnaireAnswer],
        config: GenerationConfig,
        project_detail: Optional[ProjectDetail] = None,
        project_assumption: Optional[ProjectAssumption] = None
    ) -> Dict[str, Any]:
        """
        Regenerate component with feedback (with retry loop like _generate_with_validation)
        Returns: {'success': bool, 'content': component, 'judge_result': JudgeResult, 'error': str}
        """
        for attempt in range(self.max_auto_retries):
            try:
                logger.info(f"🔄 Regeneration attempt {attempt + 1}/{self.max_auto_retries}")
                
                # Generate with feedback
                if component_type == "project_detail":
                    input_data = ProjectDetailInput(client_info, questionnaire_answers)
                    content = self.engine.generate_project_detail(
                        input_data, config, previous_content, feedback
                    )
                    judge_result = self.judge.judge_project_detail(
                        content, client_info, questionnaire_answers
                    )
                
                elif component_type == "project_assumption":
                    input_data = ProjectAssumptionInput(
                        client_info, questionnaire_answers, project_detail
                    )
                    content = self.engine.generate_project_assumption(
                        input_data, config, previous_content, feedback
                    )
                    judge_result = self.judge.judge_project_assumption(
                        content, project_detail, client_info, questionnaire_answers
                    )
                
                elif component_type == "scope_of_work":
                    input_data = ScopeOfWorkInput(
                        client_info, questionnaire_answers, project_detail, project_assumption
                    )
                    # Engine returns (ScopeOfWork, rag_tasks)
                    content, rag_tasks = self.engine.generate_scope_of_work(
                        input_data, config, previous_content, feedback, top_k=self.top_k
                    )
                    
                    # Use rag_tasks from engine (no duplicate call)
                    judge_result = self.judge.judge_scope_of_work(
                        content, project_assumption, project_detail, rag_tasks
                    )
                
                else:
                    raise ValueError(f"Unknown component type: {component_type}")
                
                # Check judge result
                if judge_result.status == "PASS":
                    logger.info(f"✅ Regeneration PASSED (Score: {judge_result.score}/100)")
                    return {
                        'success': True,
                        'content': content,
                        'judge_result': judge_result,
                        'error': None
                    }
                else:
                    logger.warning(f"❌ Regeneration attempt {attempt + 1} FAILED (Score: {judge_result.score}/100)")
                    logger.warning(f"Issues: {', '.join(judge_result.issues)}")
                    
                    if attempt < self.max_auto_retries - 1:
                        logger.info("🔄 Retrying regeneration with judge feedback...")
                        # Update feedback to include judge issues
                        feedback = f"{feedback}\n\nPrevious attempt issues:\n" + "\n".join(f"- {issue}" for issue in judge_result.issues)
                    else:
                        logger.error(f"❌ Max retries reached for regeneration")
                        return {
                            'success': False,
                            'content': content,
                            'judge_result': judge_result,
                            'error': f"Regeneration failed validation after {self.max_auto_retries} attempts. Last score: {judge_result.score}/100"
                        }
            
            except Exception as e:
                logger.error(f"❌ Error in regeneration attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_auto_retries - 1:
                    return {
                        'success': False,
                        'content': None,
                        'judge_result': None,
                        'error': str(e)
                    }
        
        return {
            'success': False,
            'content': None,
            'judge_result': None,
            'error': "Max retries exceeded"
        }
    
    def _create_failure_result(
        self,
        failed_component: str,
        result: Dict[str, Any],
        detail: ProjectDetail,
        assumption: ProjectAssumption,
        sow: ScopeOfWork,
        version: str
    ) -> OrchestrationResult:
        """Create failure result"""
        return OrchestrationResult(
            status="failure",
            project_detail=detail,
            project_assumption=assumption,
            scope_of_work=sow,
            detail_judge=result.get('judge_result'),
            assumption_judge=result.get('judge_result'),
            sow_judge=result.get('judge_result'),
            failed_component=failed_component,
            error_message=result.get('error'),
            detail_version=version,
            assumption_version=version,
            sow_version=version
        )
