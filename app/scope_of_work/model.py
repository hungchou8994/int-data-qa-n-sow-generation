from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class QuestionnaireAnswer:
    question_id: str
    question_text: str
    section: str
    answer: str


@dataclass
class ClientInformation:
    customer_name: str
    business_domain: str
    requirements: str
    audience: str
    language: str
    project_type: Optional[str] = None
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    additional_context: Optional[str] = None


@dataclass
class ProjectDetailInput:
    client_info: ClientInformation
    questionnaire_answers: List[QuestionnaireAnswer]


@dataclass
class ProjectDetail:
    detail_id: str
    customer_name: str
    business_domain: str
    
    overview: str
    key_features: List[str]  
    
    created_at: datetime
    language: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail_id": self.detail_id,
            "customer_name": self.customer_name,
            "business_domain": self.business_domain,
            "overview": self.overview,
            "key_features": self.key_features,
            "created_at": self.created_at.isoformat(),
            "language": self.language
        }


@dataclass
class ProjectAssumptionInput:
    client_info: ClientInformation
    questionnaire_answers: List[QuestionnaireAnswer]
    project_detail: ProjectDetail


@dataclass
class AssumptionSection:
    section: str
    points: List[str]


@dataclass
class ProjectAssumption:
    assumption_id: str
    customer_name: str
    business_domain: str
    
    assumptions: List[AssumptionSection]
    
    created_at: datetime
    language: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "customer_name": self.customer_name,
            "business_domain": self.business_domain,
            "assumptions": [
                {
                    "section": section.section,
                    "points": section.points
                }
                for section in self.assumptions
            ],
            "created_at": self.created_at.isoformat(),
            "language": self.language
        }


@dataclass
class GenerationConfig:
    temperature: float = 0.7
    max_retries: int = 3
    language: str = "English"





@dataclass
class ScopeOfWorkInput:
    client_info: ClientInformation
    questionnaire_answers: List[QuestionnaireAnswer]
    project_detail: ProjectDetail
    project_assumption: ProjectAssumption


@dataclass
class ScopeOfWorkTask:
    task_category: str
    task_title: str
    content: str
    man_days: float
    source: str = "generated"  # "generated" or "rag"
    similarity_score: Optional[float] = None



@dataclass
class ScopeOfWork:
    sow_id: str
    customer_name: str
    business_domain: str
    project_type: str
    
    tasks: List[ScopeOfWorkTask]
    
    total_man_days: float
    total_tasks: int
    
    created_at: datetime
    language: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sow_id": self.sow_id,
            "customer_name": self.customer_name,
            "business_domain": self.business_domain,
            "project_type": self.project_type,
            "tasks": [
                {
                    "task_category": task.task_category,
                    "task_title": task.task_title,
                    "content": task.content,
                    "man_days": task.man_days,
                    "source": task.source,
                    "similarity_score": task.similarity_score
                }
                for task in self.tasks
            ],
            "total_man_days": self.total_man_days,
            "total_tasks": self.total_tasks,
            "created_at": self.created_at.isoformat(),
            "language": self.language
        }
    
    def get_tasks_by_category(self) -> Dict[str, List[ScopeOfWorkTask]]:
        from collections import defaultdict
        grouped = defaultdict(list)
        for task in self.tasks:
            grouped[task.task_category].append(task)
        return dict(grouped)


@dataclass
class JudgeResult:
    component: str  # "project_detail", "project_assumption", "scope_of_work"
    status: str  # "PASS" or "FAIL"
    score: float  # 0-100
    feedback: str  # Detailed feedback from judge
    issues: List[str]  # List of specific issues found
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status,
            "score": self.score,
            "feedback": self.feedback,
            "issues": self.issues,
        }


@dataclass
class ComponentVersion:
    """Track versions of each component"""
    component: str
    version: str  # "v_final_auto", "v_human_1", "v_human_2", etc.
    content: Any  # ProjectDetail, ProjectAssumption, or ScopeOfWork
    judge_result: Optional[JudgeResult]
    created_at: datetime
    created_by: str  # "auto" or "human_feedback"
    

@dataclass
class LLMPrompt:
    system_prompt: str
    user_prompt: str
    context: str
    
    def format_prompt(self) -> str:
        return f"{self.system_prompt}\n\n{self.context}\n\n{self.user_prompt}" 
