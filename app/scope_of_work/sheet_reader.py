

import logging
import os
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class QuestionnaireSheetReader:
    
    def __init__(self, credentials_path: Optional[str] = None):
        """Initialize the sheet reader"""
        self.scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self.client = None
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            if not self.credentials_path or not os.path.exists(self.credentials_path):
                raise ValueError(f"Credentials file not found: {self.credentials_path}")
            
            creds = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.scope
            )
            self.client = gspread.authorize(creds)
            logger.info("Successfully authenticated with Google Sheets API")
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise
    
    def read_questionnaire_from_sheet(
        self,
        sheet_url: str,
        worksheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            # Open spreadsheet
            if sheet_url.startswith('http'):
                spreadsheet = self.client.open_by_url(sheet_url)
            else:
                spreadsheet = self.client.open_by_key(sheet_url)
            
            # Get worksheet
            if worksheet_name:
                worksheet = spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = spreadsheet.sheet1
            
            logger.info(f"Opened worksheet: {worksheet.title}")
            
            # Read all values
            all_values = worksheet.get_all_values()
            
            if len(all_values) < 5:
                raise ValueError("Sheet does not have enough data")
            
            # Parse the sheet structure
            # Row 1: Title "SURVEY QUESTIONS"
            # Row 2: Instructions (red text)
            # Row 3: Customer Name and Requirements
            # Row 4: Headers (#, Section, Question, Answer)
            # Row 5+: Question data
            
            # Extract client info from row 3
            client_row = all_values[2] if len(all_values) > 2 else []
            client_info = self._parse_client_info(client_row)
            
            # Extract questions and answers
            answers = []
            current_section = ""
            
            for i, row in enumerate(all_values[4:], start=5):  # Start from row 5 (index 4)
                if len(row) < 4:
                    continue
                
                num, section, question, answer = row[0], row[1], row[2], row[3]
                
                # Skip empty rows or header row
                if not question or question.lower() == 'question':
                    continue
                
                # Update current section if not empty
                if section and section.strip():
                    current_section = section.strip()
                
                # Create answer object
                if answer and answer.strip():
                    answers.append({
                        'question_id': f'q{num}' if num else f'q{i}',
                        'section': current_section,
                        'question_text': question.strip(),
                        'answer': answer.strip()
                    })
            
            logger.info(f"Extracted {len(answers)} answers from sheet")
            
            return {
                'client_info': client_info,
                'answers': answers
            }
            
        except Exception as e:
            logger.error(f"Error reading questionnaire from sheet: {str(e)}")
            raise
    
    def _parse_client_info(self, client_row: List[str]) -> Dict[str, str]:
        """Parse client information from row 3"""
        try:
            # Expected format: "Customer Name: Cloud Ace\nRequirements: Build a support tool..."
            if len(client_row) < 1:
                return {
                    'customer_name': 'Unknown',
                    'requirements': ''
                }
            
            # First cell contains customer info
            info_text = client_row[0] if client_row else ''
            
            customer_name = ''
            requirements = ''
            
            # Parse line by line
            lines = info_text.split('\n')
            for line in lines:
                if 'Customer Name:' in line or 'customer name:' in line.lower():
                    customer_name = line.split(':', 1)[1].strip() if ':' in line else ''
                elif 'Requirements:' in line or 'requirements:' in line.lower():
                    requirements = line.split(':', 1)[1].strip() if ':' in line else ''
            
            # Fallback: if not found in first cell, check other cells
            if not customer_name and len(client_row) > 1:
                for cell in client_row:
                    if 'Cloud Ace' in cell or 'customer' in cell.lower():
                        customer_name = cell.split(':', 1)[1].strip() if ':' in cell else cell.strip()
                        break
            
            return {
                'customer_name': customer_name or 'Unknown',
                'requirements': requirements or 'Please provide requirements'
            }
            
        except Exception as e:
            logger.error(f"Error parsing client info: {str(e)}")
            return {
                'customer_name': 'Unknown',
                'requirements': ''
            }


def read_questionnaire_from_google_sheet(
    sheet_url: str,
    worksheet_name: Optional[str] = None,
    credentials_path: Optional[str] = None
) -> Dict[str, Any]:

    reader = QuestionnaireSheetReader(credentials_path)
    return reader.read_questionnaire_from_sheet(sheet_url, worksheet_name)
