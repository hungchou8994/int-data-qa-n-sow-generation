"""
Data models for SOW Google Sheets integration
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SheetOperation:
    success: bool
    message: str
    spreadsheet_url: Optional[str] = None
    spreadsheet_id: Optional[str] = None
    error_message: Optional[str] = None
    
    @staticmethod
    def success_result(message: str, spreadsheet_url: str = None, spreadsheet_id: str = None):
        return SheetOperation(
            success=True,
            message=message,
            spreadsheet_url=spreadsheet_url,
            spreadsheet_id=spreadsheet_id
        )
    
    @staticmethod
    def error_result(error_message: str):
        return SheetOperation(
            success=False,
            message="Export failed",
            error_message=error_message
        )
