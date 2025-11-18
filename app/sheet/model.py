

import sys
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import from questionaires module
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from questionaires.model import QuestionnaireOutput


@dataclass
class QuestionnaireResponse:
    """Response data for saving to Google Sheets"""
    response_id: str
    questionnaire: QuestionnaireOutput
    responses: Dict[str, Any]  # question_id -> response
    completed_at: datetime
    
    def to_sheet_row(self) -> List[Any]:
        """Convert to sheet row format"""
        return [
            self.response_id,
            self.questionnaire.customer_name,
            self.questionnaire.business_domain,
            self.questionnaire.questionnaire_id,
            self.questionnaire.title,
            self.completed_at.isoformat(),
            self.questionnaire.total_questions,
            str(self.responses)  # JSON string of all responses
        ]
    
    @classmethod
    def get_sheet_headers(cls) -> List[str]:
        """Get headers for sheet columns"""
        return [
            "Response ID",
            "Customer Name", 
            "Business Domain",
            "Questionnaire ID",
            "Questionnaire Title",
            "Completed At",
            "Total Questions",
            "Responses (JSON)"
        ]


@dataclass
class SheetOperation:
    """Result of a sheet operation"""
    success: bool
    message: str
    error_message: Optional[str] = None
    spreadsheet_url: Optional[str] = None
    spreadsheet_id: Optional[str] = None
    
    @classmethod
    def success_result(cls, message: str, spreadsheet_url: Optional[str] = None, spreadsheet_id: Optional[str] = None) -> 'SheetOperation':
        """Create success result"""
        return cls(
            success=True, 
            message=message,
            spreadsheet_url=spreadsheet_url,
            spreadsheet_id=spreadsheet_id
        )
    
    @classmethod
    def error_result(cls, error_message: str) -> 'SheetOperation':
        """Create error result"""
        return cls(success=False, message="Operation failed", error_message=error_message)
