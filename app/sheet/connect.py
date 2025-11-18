import logging
import os
from typing import Optional, Dict, List
from datetime import datetime

try:
    import gspread
    from google.oauth2.service_account import Credentials
    from gspread.utils import rowcol_to_a1
    from googleapiclient.discovery import build
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from questionaires.model import QuestionnaireOutput

from .model import QuestionnaireResponse, SheetOperation

logger = logging.getLogger(__name__)


class GoogleSheetsConnector:
    
    def __init__(self):
        self.client = None
        self.drive_service = None
        self.spreadsheet = None
        self.worksheet = None
        
        if not GSPREAD_AVAILABLE:
            logger.error("gspread library not available")
            raise ImportError("gspread library required")
    
    def authenticate(self) -> bool:
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file'
            ]
            
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                credentials = Credentials.from_service_account_file(credentials_path, scopes=scopes)
                self.client = gspread.authorize(credentials)
                self.drive_service = build('drive', 'v3', credentials=credentials)
                logger.info("Authenticated with Google Sheets and Drive API")
                return True
            else:
                logger.error("No credentials found")
                return False
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def connect_to_sheet(self, spreadsheet_id: str, worksheet_name: str = "Responses") -> bool:
        try:
            if not self.client and not self.authenticate():
                return False
            
            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            
            try:
                self.worksheet = self.spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                self.worksheet = self.spreadsheet.add_worksheet(
                    title=worksheet_name, rows=1000, cols=10
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    def write_questionnaire_response(self, response: QuestionnaireResponse) -> SheetOperation:
        try:
            if not self.worksheet:
                return SheetOperation.error_result("No worksheet connected")
            
            existing_values = self.worksheet.row_values(1)
            headers = QuestionnaireResponse.get_sheet_headers()
            if existing_values != headers:
                self.worksheet.clear()
                self.worksheet.append_row(headers)
            
            row_data = response.to_sheet_row()
            self.worksheet.append_row(row_data)
            
            return SheetOperation.success_result(f"Response saved for {response.customer_name}")
            
        except Exception as e:
            logger.error(f"Failed to write response: {e}")
            return SheetOperation.error_result(str(e))
    
    def export_questionnaire_to_existing_sheet(
        self,
        spreadsheet_url: str,
        questionnaire: QuestionnaireOutput,
        judge_result: Optional[Dict] = None,
        worksheet_name: str = "Questionnaire"
    ) -> SheetOperation:

        try:
            if not self.client and not self.authenticate():
                return SheetOperation.error_result("Authentication failed")
            
            # Extract spreadsheet ID from URL
            spreadsheet_id = self._extract_spreadsheet_id(spreadsheet_url)
            if not spreadsheet_id:
                return SheetOperation.error_result("Invalid Google Sheets URL")
            
            logger.info(f"Opening existing spreadsheet: {spreadsheet_id}")
            
            # Open the spreadsheet
            try:
                spreadsheet = self.client.open_by_key(spreadsheet_id)
            except Exception as e:
                return SheetOperation.error_result(
                    f"Cannot access spreadsheet. Make sure you've shared it with the service account: {str(e)}"
                )
            
            # Create or get worksheet
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
                logger.info(f"Using existing worksheet: {worksheet_name}")
                # Clear existing content
                worksheet.clear()
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=5)
                logger.info(f"Created new worksheet: {worksheet_name}")
            
            # Format the questionnaire
            self._format_questionnaire_sheet(worksheet, questionnaire, judge_result)
            
            # Get spreadsheet URL
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}/edit"
            
            logger.info(f"✅ Questionnaire exported successfully to existing sheet")
            return SheetOperation.success_result(
                message=f"Questionnaire exported to '{worksheet_name}' worksheet",
                spreadsheet_url=spreadsheet_url,
                spreadsheet_id=spreadsheet.id
            )
            
        except Exception as e:
            logger.error(f"Failed to export questionnaire: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return SheetOperation.error_result(str(e))
    
    def _extract_spreadsheet_id(self, url_or_id: str) -> Optional[str]:
        # If it's already just an ID (no slashes)
        if '/' not in url_or_id:
            return url_or_id
        
        # Extract from URL: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
        try:
            if '/spreadsheets/d/' in url_or_id:
                parts = url_or_id.split('/spreadsheets/d/')[1]
                spreadsheet_id = parts.split('/')[0]
                return spreadsheet_id
        except:
            pass
        
        return None
    
    def export_questionnaire_to_new_sheet(
        self, 
        questionnaire: QuestionnaireOutput,
        judge_result: Optional[Dict] = None
    ) -> SheetOperation:

        try:
            if not self.client and not self.authenticate():
                return SheetOperation.error_result("Authentication failed")
            
            # Create new spreadsheet
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sheet_title = f"SURVEY QUESTIONS - {questionnaire.customer_name} - {timestamp}"
            
            logger.info(f"Creating new Google Sheet: {sheet_title}")
            spreadsheet = self.client.create(sheet_title)
            
            # Immediately remove from service account's "My Drive" to save quota
            # This keeps the file but removes it from the service account's storage
            try:
                if self.drive_service:
                    # Get current parents
                    file = self.drive_service.files().get(
                        fileId=spreadsheet.id, 
                        fields='parents'
                    ).execute()
                    
                    previous_parents = ",".join(file.get('parents', []))
                    
                    # Remove from all parents (removes from "My Drive" but keeps file accessible via link)
                    if previous_parents:
                        self.drive_service.files().update(
                            fileId=spreadsheet.id,
                            removeParents=previous_parents,
                            fields='id, parents'
                        ).execute()
                        logger.info(f"✅ Removed file from service account's My Drive to save quota")
            except Exception as e:
                logger.warning(f"Could not remove from My Drive (file still created): {e}")
            
            worksheet = spreadsheet.sheet1
            worksheet.update_title("Questionnaire")
            
            # Build the sheet content
            self._format_questionnaire_sheet(worksheet, questionnaire, judge_result)
            
            # Share with anyone with link (view only)
            try:
                spreadsheet.share(None, perm_type='anyone', role='reader', with_link=True)
                logger.info("Sheet shared with public link")
            except Exception as e:
                logger.warning(f"Could not set public sharing: {e}")
            
            # Get spreadsheet URL
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet.id}/edit"
            
            logger.info(f"✅ Questionnaire exported successfully: {spreadsheet_url}")
            return SheetOperation.success_result(
                message=f"Questionnaire exported successfully",
                spreadsheet_url=spreadsheet_url,
                spreadsheet_id=spreadsheet.id
            )
            
        except Exception as e:
            logger.error(f"Failed to export questionnaire: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return SheetOperation.error_result(str(e))
    
    def _format_questionnaire_sheet(
        self, 
        worksheet, 
        questionnaire: QuestionnaireOutput,
        judge_result: Optional[Dict] = None
    ):
        """Format the questionnaire sheet with beautiful styling"""
        
        # Prepare data rows
        data = []
        current_row = 1
        
        # Row 1: Main Title
        data.append(["SURVEY QUESTIONS ON " + questionnaire.business_domain.upper() + " PROJECT"])
        
        # Row 2: Instruction (merged)
        instruction = "* Please provide detailed answers. If possible, please provide Cloud Ace with sample data / architecture / any related examples from your company."
        data.append([instruction])
        
        # Row 3: Customer info
        customer_info = f"Customer: {questionnaire.customer_name}\nRequirements: {questionnaire.description}"
        data.append([customer_info])
        
        # Row 4: Table Header
        data.append(["No", "Section", "Question", "Answer", "Notes"])
        
        # Group questions by section
        sections = {}
        for q in questionnaire.questions:
            if q.section not in sections:
                sections[q.section] = []
            sections[q.section].append(q)
        
        # Add questions
        section_number = 1
        for section_name, questions in sections.items():
            for i, question in enumerate(questions):
                row = [
                    section_number if i == 0 else "",  # Number only for first question in section
                    section_name if i == 0 else "",  # Section only for first question
                    question.question_text,
                    "",  # Empty Answer column
                    ""   # Empty Notes column
                ]
                data.append(row)
            section_number += 1
        
        


        # Write all data at once
        worksheet.update('A1', data)


        current_data_row = 5  # Start of data rows
        for section_name, questions in sections.items():
            num_questions = len(questions)
            if num_questions > 1:  # Only merge if section has more than 1 question
                no_merge_range = f'A{current_data_row}:A{current_data_row + num_questions - 1}'
                section_merge_range = f'B{current_data_row}:B{current_data_row + num_questions - 1}'
                worksheet.merge_cells(no_merge_range)
                worksheet.merge_cells(section_merge_range)
                logger.info(f"Merged No: {no_merge_range}, Section: {section_merge_range}")
            current_data_row += num_questions
            
        # Apply formatting
        self._apply_formatting(worksheet, questionnaire, len(data), len(sections))

        
        logger.info(f"Formatted sheet with {len(data)} rows")
    
    def _apply_formatting(self, worksheet, questionnaire: QuestionnaireOutput, total_rows: int, section_count: int):
        """Apply beautiful formatting to the sheet"""
        try:
            # First, unmerge all cells to avoid conflicts
            try:
                # Get all merged ranges
                merged_ranges = worksheet.spreadsheet.fetch_sheet_metadata()['sheets'][0].get('merges', [])
                if merged_ranges:
                    unmerge_requests = []
                    for merge in merged_ranges:
                        unmerge_requests.append({
                            'unmergeCells': {
                                'range': {
                                    'sheetId': worksheet.id,
                                    'startRowIndex': merge['startRowIndex'],
                                    'endRowIndex': merge['endRowIndex'],
                                    'startColumnIndex': merge['startColumnIndex'],
                                    'endColumnIndex': merge['endColumnIndex']
                                }
                            }
                        })
                    
                    if unmerge_requests:
                        worksheet.spreadsheet.batch_update({'requests': unmerge_requests})
                        logger.info(f"✅ Unmerged {len(unmerge_requests)} existing merged ranges")
            except Exception as e:
                logger.warning(f"Could not unmerge cells: {e}")
            
            # Set column widths using batch update (pixels)
            body = {
                'requests': [
                    {
                        'updateDimensionProperties': {
                            'range': {
                                'sheetId': worksheet.id,
                                'dimension': 'COLUMNS',
                                'startIndex': 0,
                                'endIndex': 1
                            },
                            'properties': {'pixelSize': 50},
                            'fields': 'pixelSize'
                        }
                    },
                    {
                        'updateDimensionProperties': {
                            'range': {
                                'sheetId': worksheet.id,
                                'dimension': 'COLUMNS',
                                'startIndex': 1,
                                'endIndex': 2
                            },
                            'properties': {'pixelSize': 200},
                            'fields': 'pixelSize'
                        }
                    },
                    {
                        'updateDimensionProperties': {
                            'range': {
                                'sheetId': worksheet.id,
                                'dimension': 'COLUMNS',
                                'startIndex': 2,
                                'endIndex': 3
                            },
                            'properties': {'pixelSize': 500},
                            'fields': 'pixelSize'
                        }
                    },
                    {
                        'updateDimensionProperties': {
                            'range': {
                                'sheetId': worksheet.id,
                                'dimension': 'COLUMNS',
                                'startIndex': 3,
                                'endIndex': 4
                            },
                            'properties': {'pixelSize': 500},
                            'fields': 'pixelSize'
                        }
                    },
                    {
                        'updateDimensionProperties': {
                            'range': {
                                'sheetId': worksheet.id,
                                'dimension': 'COLUMNS',
                                'startIndex': 4,
                                'endIndex': 5
                            },
                            'properties': {'pixelSize': 200},
                            'fields': 'pixelSize'
                        }
                    }
                ]
            }
            worksheet.spreadsheet.batch_update(body)
            logger.info("✅ Column widths set successfully")
            
            # Row 1: Main Title - Merge first, then format
            worksheet.merge_cells('A1:E1')
            worksheet.format('A1:E1', {
                'backgroundColor': {'red': 1, 'green': 1, 'blue': 1},  # white
                'textFormat': {
                    'foregroundColor': {'red': 0.26, 'green': 0.52, 'blue': 0.96},  # blue
                    'fontSize': 24,
                    'bold': True,
                    'fontFamily': 'Times New Roman'
                },
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE'
            })
            
            # Row 2: Instruction - Red text, italic
            worksheet.merge_cells('A2:E2')
            worksheet.format('A2:E2', {
                'textFormat': {
                    'foregroundColor': {'red': 1, 'green': 0, 'blue': 0},  # Red
                    'italic': True,
                    'fontSize': 12,
                    'fontFamily': 'Times New Roman'
                },
                'verticalAlignment': 'TOP',
                'wrapStrategy': 'WRAP'
            })
            
            # Row 3: Customer info
            worksheet.merge_cells('A3:E3')
            worksheet.format('A3:E3', {
                'textFormat': {'bold': True,
                               'fontSize': 12,
                               'fontFamily': 'Times New Roman'},
                'verticalAlignment': 'TOP',
                'wrapStrategy': 'WRAP'
            })
            
            # Row 4: Table Header - Dark blue background, white text, bold, centered
            worksheet.format('A4:E4', {
                'backgroundColor': {'red': 0.2, 'green': 0.33, 'blue': 0.61},  # Dark blue
                'textFormat': {
                    'foregroundColor': {'red': 1, 'green': 1, 'blue': 1},  # White
                    'fontSize': 12,
                    'bold': True,
                    'fontFamily': 'Times New Roman'
                },
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE',
                'borders': {
                    'top': {'style': 'SOLID', 'width': 2},
                    'bottom': {'style': 'SOLID', 'width': 2},
                    'left': {'style': 'SOLID', 'width': 2},
                    'right': {'style': 'SOLID', 'width': 2}
                }
            })
            
            # Data rows: Add borders and wrap text
            if total_rows > 4:
                data_range = f'A5:E{total_rows}'
                worksheet.format(data_range, {
                    'borders': {
                        'top': {'style': 'SOLID', 'width': 1},
                        'bottom': {'style': 'SOLID', 'width': 1},
                        'left': {'style': 'SOLID', 'width': 1},
                        'right': {'style': 'SOLID', 'width': 1}
                    },
                    'verticalAlignment': 'TOP',
                    'wrapStrategy': 'WRAP',
                    'textFormat': {'fontSize': 12, 'fontFamily': 'Times New Roman'}
                })
                
                # No & Section columns: Center alignment, bold
                worksheet.format(f'A5:B{total_rows}', {
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE',
                    'textFormat': {'fontSize': 12, 'fontFamily': 'Times New Roman'}
                })
            
            
            # Freeze header rows
            worksheet.freeze(rows=4)
            
            logger.info("✅ Formatting applied successfully")
            
        except Exception as e:
            logger.warning(f"Some formatting failed: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            # Continue even if formatting fails