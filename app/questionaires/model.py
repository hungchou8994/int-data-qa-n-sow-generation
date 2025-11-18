"""
Data models for questionnaires module
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class QuestionnaireInput:
    customer_name: str
    requirements: str
    business_domain: str
    audience: str
    language: str
    project_type: Optional[str] = None
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    additional_context: Optional[str] = None
    
@dataclass
class Question:
    id: str
    section: str
    question_text: str
    title: Optional[str] = None
    similarity_score: Optional[float] = None


@dataclass
class QuestionnaireOutput:
    questionnaire_id: str
    title: str
    description: str
    customer_name: str
    business_domain: str
    audience: str
    questions: List[Question]
    created_at: datetime
    total_questions: int
    language: str


@dataclass
class RetrievalResult:
    title: str
    section: str
    question: str
    similarity_score: float
    distance: float


@dataclass
class LLMPrompt:
    system_prompt: str
    user_prompt: str
    context: str
    retrieved_questions: List[RetrievalResult]
    
    def format_prompt(self) -> str:
        context_text = f"Context: {self.context}\n\n"
        
        retrieved_text = "Retrieved Similar Questions:\n"
        for i, result in enumerate(self.retrieved_questions, 1):
            retrieved_text += f"{i}. [{result.section}] {result.question} (Score: {result.similarity_score:.3f})\n"
        
        return f"{self.system_prompt}\n\n{context_text}{retrieved_text}\n\nUser Request: {self.user_prompt}"


@dataclass
class GenerationConfig:
    max_questions: int = 20
    min_questions: int = 5
    retrieval_top_k: int = 10
    similarity_threshold: float = 0.7
    include_sections: Optional[List[str]] = None
    exclude_sections: Optional[List[str]] = None
    temperature: float = 0.7
