"""
Google Sheets connector for SOW export
"""

import logging
import os
from typing import Optional, Dict, List
from datetime import datetime

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scope_of_work.model import ProjectDetail, ProjectAssumption, ScopeOfWork

from .model import SheetOperation

logger = logging.getLogger(__name__)


class SOWGoogleSheetsConnector:
    
    def __init__(self):
        self.client = None
        
        if not GSPREAD_AVAILABLE:
            logger.error("gspread library not available")
            raise ImportError("gspread library required")
    
    def authenticate(self) -> bool:
        """Authenticate with Google Sheets API"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
                self.client = gspread.authorize(credentials)
                logger.info("Authenticated with Google Sheets API")
                return True
            else:
                logger.error("No credentials found")
                return False
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def export_sow_to_sheet(
        self,
        spreadsheet_url: str,
        project_detail: ProjectDetail,
        project_assumption: ProjectAssumption,
        scope_of_work: ScopeOfWork,
        overview_worksheet_name: str = "Overview",
        sow_worksheet_name: str = "Scope of Work"
    ) -> SheetOperation:
        """
        Export SOW to Google Sheets with 2 worksheets:
        1. Overview: Project Detail + Project Assumption
        2. Scope of Work: Task breakdown table
        """
        try:
            if not self.client and not self.authenticate():
                return SheetOperation.error_result("Authentication failed")
            
            # Extract spreadsheet ID from URL
            spreadsheet_id = self._extract_spreadsheet_id(spreadsheet_url)
            if not spreadsheet_id:
                return SheetOperation.error_result("Invalid Google Sheets URL")
            
            logger.info(f"Opening spreadsheet: {spreadsheet_id}")
            
            # Open spreadsheet
            try:
                spreadsheet = self.client.open_by_key(spreadsheet_id)
            except gspread.exceptions.SpreadsheetNotFound:
                return SheetOperation.error_result(
                    "Spreadsheet not found. Make sure you've shared it with the service account."
                )
            except Exception as e:
                return SheetOperation.error_result(f"Cannot access spreadsheet: {str(e)}")
            
            # Create/recreate Overview worksheet
            overview_ws = self._create_or_replace_worksheet(spreadsheet, overview_worksheet_name, rows=100, cols=10)
            self._format_overview_worksheet(overview_ws, project_detail, project_assumption)
            
            # Create/recreate Scope of Work worksheet
            sow_ws = self._create_or_replace_worksheet(spreadsheet, sow_worksheet_name, rows=200, cols=15)
            self._format_sow_worksheet(sow_ws, scope_of_work)
            
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}/edit"
            
            logger.info(f"✅ SOW exported successfully")
            return SheetOperation.success_result(
                message=f"SOW exported to '{overview_worksheet_name}' and '{sow_worksheet_name}' worksheets",
                spreadsheet_url=spreadsheet_url,
                spreadsheet_id=spreadsheet.id
            )
            
        except Exception as e:
            logger.error(f"Failed to export SOW: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return SheetOperation.error_result(str(e))
    
    def _extract_spreadsheet_id(self, url_or_id: str) -> Optional[str]:
        """Extract spreadsheet ID from URL or return ID if already provided"""
        if '/' not in url_or_id:
            return url_or_id
        
        try:
            if '/spreadsheets/d/' in url_or_id:
                parts = url_or_id.split('/spreadsheets/d/')[1]
                return parts.split('/')[0]
        except Exception as e:
            logger.error(f"Failed to extract spreadsheet ID: {e}")
        
        return None
    
    def _create_or_replace_worksheet(self, spreadsheet, worksheet_name: str, rows: int, cols: int):
        """Delete old worksheet if exists, then create fresh one"""
        try:
            old_ws = spreadsheet.worksheet(worksheet_name)
            spreadsheet.del_worksheet(old_ws)
            logger.info(f"✅ Deleted existing worksheet: {worksheet_name}")
        except gspread.WorksheetNotFound:
            logger.info(f"Worksheet '{worksheet_name}' does not exist, will create new one")
        
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=rows, cols=cols)
        logger.info(f"✅ Created new worksheet: {worksheet_name}")
        return worksheet
    
    def _format_overview_worksheet(
        self,
        worksheet,
        project_detail: ProjectDetail,
        project_assumption: ProjectAssumption
    ):
        """Format Overview worksheet with Project Detail and Assumption"""
        data = []
        
        # Header
        data.append(["Project Overview"])
        data.append([])  # Empty row
        
        # Metadata
        data.append(["PROJECT TITLE", "X", "", "", "COMPANY NAME", "X"])
        data.append(["PROJECT MANAGER", "TBD", "", "", "START DATE", ""])
        data.append(["TECHNICAL LEAD", "TBD", "", "", "END DATE", ""])
        data.append([])  # Empty row
        
        # Project Detail section
        data.append(["PROJECT DETAIL", "", "", "", "PROJECT ASSUMPTION"])
        
        # Overview
        overview_lines = project_detail.overview.split('\n')
        data.append([f"Overview: {overview_lines[0]}" if overview_lines else "Overview:", "", "", "", "Data Scope"])
        
        # Key Features
        data.append([])
        for i, feature in enumerate(project_detail.key_features, 1):
            if i == 1:
                data.append([f"{i}. {feature}", "", "", "", ""])
            else:
                data.append([f"{i}. {feature}", "", "", "", ""])
        
        # Project Assumptions (right column)
        assumption_start_row = 7  # Row where assumptions start
        for section in project_assumption.assumptions:
            data.append([])
            for point in section.points:
                data.append(["", "", "", "", point])
        
        # Write data
        worksheet.update('A1', data)
        
        # Apply formatting
        self._apply_overview_formatting(worksheet, len(data))
    
    def _format_sow_worksheet(self, worksheet, sow: ScopeOfWork):
        """Format Scope of Work worksheet with task breakdown table"""
        data = []
        
        # Header row
        headers = [
            "Item #",
            "Priority", 
            "Task",
            "Task Detail",
            "Man-days",
            "Progress",
            "Owner\nCustomer",
            "Owner\nCloud Ace",
            "Support\nCloud Ace",
            "Start Date",
            "End Date",
            "Status",
            "Cloud Ace Notes",
            "Customer Notes",
            "Reference"
        ]
        data.append(headers)
        
        # Group tasks by category
        grouped = sow.get_tasks_by_category()
        item_number = 1
        
        for category, tasks in grouped.items():
            # Category header row
            category_total_days = sum(task.man_days for task in tasks)
            data.append([
                str(item_number),
                "",
                category,
                "",
                str(category_total_days),
                "", "", "", "", "", "", "", "", "", ""
            ])
            
            # Task rows
            for i, task in enumerate(tasks, 1):
                task_number = f"{item_number}.{i}"
                data.append([
                    task_number,
                    "High",  # Default priority
                    task.task_title,
                    task.content,
                    str(task.man_days),
                    "Not Yet",  # Default progress
                    "",  # Owner Customer
                    "",  # Owner Cloud Ace
                    "",  # Support Cloud Ace
                    "",  # Start Date
                    "",  # End Date
                    "",  # Status
                    "",  # Cloud Ace Notes
                    "",  # Customer Notes
                    ""   # Reference
                ])
            
            item_number += 1
        
        # Write data
        worksheet.update('A1', data)
        
        # Apply formatting
        self._apply_sow_formatting(worksheet, len(data), len(headers))
    
    def _apply_overview_formatting(self, worksheet, total_rows: int):
        """Apply formatting to Overview worksheet"""
        try:
            # Title (Row 1)
            worksheet.merge_cells('A1:F1')
            worksheet.format('A1:F1', {
                'textFormat': {
                    'fontSize': 24,
                    'bold': True,
                    'fontFamily': 'Arial'
                },
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE'
            })
            
            # Metadata section (Rows 3-5)
            worksheet.format('A3:F5', {
                'textFormat': {
                    'fontSize': 11,
                    'bold': True,
                    'fontFamily': 'Arial'
                },
                'borders': {
                    'top': {'style': 'SOLID', 'width': 1},
                    'bottom': {'style': 'SOLID', 'width': 1},
                    'left': {'style': 'SOLID', 'width': 1},
                    'right': {'style': 'SOLID', 'width': 1}
                }
            })
            
            # Section headers (Row 7)
            worksheet.format('A7:D7', {
                'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.8},
                'textFormat': {
                    'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                    'fontSize': 12,
                    'bold': True,
                    'fontFamily': 'Arial'
                }
            })
            
            worksheet.format('E7:F7', {
                'backgroundColor': {'red': 0.4, 'green': 0.6, 'blue': 0.9},
                'textFormat': {
                    'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                    'fontSize': 12,
                    'bold': True,
                    'fontFamily': 'Arial'
                }
            })
            
            # Set column widths
            body = {
                'requests': [
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1},
                        'properties': {'pixelSize': 250},
                        'fields': 'pixelSize'
                    }},
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 4, 'endIndex': 6},
                        'properties': {'pixelSize': 250},
                        'fields': 'pixelSize'
                    }}
                ]
            }
            worksheet.spreadsheet.batch_update(body)
            
            logger.info("✅ Overview formatting applied")
            
        except Exception as e:
            logger.warning(f"Some formatting failed: {e}")
    
    def _apply_sow_formatting(self, worksheet, total_rows: int, total_cols: int):
        """Apply formatting to SOW worksheet"""
        try:
            # Header row
            worksheet.format('A1:O1', {
                'backgroundColor': {'red': 0.2, 'green': 0.33, 'blue': 0.61},
                'textFormat': {
                    'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},
                    'fontSize': 11,
                    'bold': True,
                    'fontFamily': 'Arial'
                },
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE',
                'wrapStrategy': 'WRAP',
                'borders': {
                    'top': {'style': 'SOLID', 'width': 2},
                    'bottom': {'style': 'SOLID', 'width': 2},
                    'left': {'style': 'SOLID', 'width': 2},
                    'right': {'style': 'SOLID', 'width': 2}
                }
            })
            
            # Data rows
            if total_rows > 1:
                data_range = f'A2:O{total_rows}'
                worksheet.format(data_range, {
                    'borders': {
                        'top': {'style': 'SOLID', 'width': 1},
                        'bottom': {'style': 'SOLID', 'width': 1},
                        'left': {'style': 'SOLID', 'width': 1},
                        'right': {'style': 'SOLID', 'width': 1}
                    },
                    'verticalAlignment': 'TOP',
                    'wrapStrategy': 'WRAP',
                    'textFormat': {'fontSize': 10, 'fontFamily': 'Arial'}
                })
            
            # Set column widths
            body = {
                'requests': [
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': 1},
                        'properties': {'pixelSize': 60},  # Item #
                        'fields': 'pixelSize'
                    }},
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 1, 'endIndex': 2},
                        'properties': {'pixelSize': 80},  # Priority
                        'fields': 'pixelSize'
                    }},
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': 3},
                        'properties': {'pixelSize': 250},  # Task
                        'fields': 'pixelSize'
                    }},
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 3, 'endIndex': 4},
                        'properties': {'pixelSize': 400},  # Task Detail
                        'fields': 'pixelSize'
                    }},
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 4, 'endIndex': 5},
                        'properties': {'pixelSize': 80},  # Man-days
                        'fields': 'pixelSize'
                    }},
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 5, 'endIndex': 6},
                        'properties': {'pixelSize': 100},  # Progress
                        'fields': 'pixelSize'
                    }},
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 6, 'endIndex': 9},
                        'properties': {'pixelSize': 120},  # Owners & Support
                        'fields': 'pixelSize'
                    }},
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 9, 'endIndex': 11},
                        'properties': {'pixelSize': 100},  # Dates
                        'fields': 'pixelSize'
                    }},
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 11, 'endIndex': 12},
                        'properties': {'pixelSize': 100},  # Status
                        'fields': 'pixelSize'
                    }},
                    {'updateDimensionProperties': {
                        'range': {'sheetId': worksheet.id, 'dimension': 'COLUMNS', 'startIndex': 12, 'endIndex': 15},
                        'properties': {'pixelSize': 150},  # Notes & Reference
                        'fields': 'pixelSize'
                    }}
                ]
            }
            worksheet.spreadsheet.batch_update(body)
            
            # Freeze header row
            worksheet.freeze(rows=1)
            
            logger.info("✅ SOW formatting applied")
            
        except Exception as e:
            logger.warning(f"Some formatting failed: {e}")
