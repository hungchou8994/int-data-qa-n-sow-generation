import os
import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from google.auth import default
from typing import List, Dict, Optional, Any
import logging
from google import genai
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv('GOOGLE_API_KEY')
client = genai.Client(api_key=api_key)

class sow_reader:
    def __init__(self, credentials_path: Optional[str] = None, credentials_json: Optional[Dict] = None):
        self.scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/cloud-platform'
        ]
        self.client = None
        self._authenticate(credentials_path, credentials_json)
    
    def _authenticate(self, credentials_path: Optional[str], credentials_json: Optional[Dict]):
        try:
            creds = None
            
            if credentials_json:
                creds = Credentials.from_service_account_info(credentials_json, scopes=self.scope)
                logger.info("Use credentials from dictionary")
            elif credentials_path and os.path.exists(credentials_path):
                creds = Credentials.from_service_account_file(credentials_path, scopes=self.scope)
                logger.info(f"Use credentials from file: {credentials_path}")
            else:
                creds_env = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if creds_env:
                    creds_dict = json.loads(creds_env)
                    creds = Credentials.from_service_account_info(creds_dict, scopes=self.scope)
                    logger.info("Use credentials from environment variable GOOGLE_APPLICATION_CREDENTIALS")
                else:
                    try:
                        creds, project = default(scopes=self.scope)
                        logger.info(f"Use Application Default Credentials (ADC) for project: {project}")
                    except Exception as adc_error:
                        raise ValueError(
                            "Cannot find Google credentials. Please:\n"
                            "1. Provide credentials_path or credentials_json, or\n"
                            "2. Set GOOGLE_CREDENTIALS environment variable, or\n"
                            "3. Run 'gcloud auth application-default login' to setup ADC\n"
                            f"ADC error: {str(adc_error)}"
                        )
            
            self.client = gspread.authorize(creds)
            logger.info("Connected to Google Sheets API successfully")
            
        except Exception as e:
            logger.error(f"Error when authenticating Google Sheets API: {str(e)}")
            raise
    def get_sheet_by_url(self, sheet_url: str) -> gspread.Spreadsheet:
        try:
            spreadsheet = self.client.open_by_url(sheet_url)
            logger.info(f"Opened spreadsheet by URL: {sheet_url}")
            return spreadsheet
        except Exception as e:
            logger.error(f"Error opening spreadsheet by URL: {str(e)}")
            raise
    def read_sow_sheet_data(self, sheet_url: str, worksheet_name: str = 'SoW (Hung)') -> pd.DataFrame:
        try:
            spreadsheet = self.get_sheet_by_url(sheet_url)
            worksheet = spreadsheet.worksheet(worksheet_name)
            data = worksheet.get_all_values()
            df = pd.DataFrame(data)
            logger.info(f"Read data from worksheet: {worksheet_name}")
            return df
        except Exception as e:
            logger.error(f"Error reading data from sheet: {str(e)}")
            raise
  
    def list_worksheets(self, sheet_url: str) -> List[str]:
        try:
            spreadsheet = self.get_sheet_by_url(sheet_url)
            worksheets = spreadsheet.worksheets()
            worksheet_titles = [ws.title for ws in worksheets]
            logger.info(f"Listed worksheets in spreadsheet: {sheet_url}")
            return worksheet_titles
        except Exception as e:
            logger.error(f"Error listing worksheets: {str(e)}")
            raise
    
    def format_sow_data(self, df: pd.DataFrame, prj_id: str, project_type: str) -> pd.DataFrame:
        try:
            header_row_index = 1
            header_row = df.iloc[header_row_index]

            data = df.values[header_row_index + 1:]

            data_df = pd.DataFrame(data, columns=header_row)
            required_cols = ['Item #', 'Priority', 'Task', 'Task Detail', 'Man-days']
            data_df = data_df[required_cols]

            chunks = []
            current_task_category = None

            for _, row in data_df.iterrows():
                item_num = str(row['Item #']).strip()   
                priority = str(row['Priority']).strip()
                task_title = str(row['Task']).strip()
                task_detail = str(row['Task Detail']).strip()

                try:
                    man_days = float(str(row['Man-days']).strip())
                except (ValueError, TypeError):
                    man_days = None
                
                if '.' not in item_num and item_num != "" and task_title:
                    current_task_category = task_title
                    logger.info(f"Phát hiện Category mới: {current_task_category}")
                    continue
                    
                if '.' in item_num and task_title:
                    content = f"Task: {task_title}. Detail: {task_detail}"

                    chunk_data ={
                        'prj_id': prj_id,
                        'project_type': project_type,
                        'task_category': current_task_category,
                        'item_number': item_num,
                        'task_title': task_title,
                        'priority': priority,
                        'content': content,
                        'man_days': man_days
                    }
                    chunks.append(chunk_data)
            logger.info(f"Formatted SoW data with {len(chunks)} tasks in project {prj_id}")
            return pd.DataFrame(chunks)

        except Exception as e:
            logger.error(f"Error formatting SoW data: {str(e)}")
            raise

def read_format_sow(sheet_url: str, worksheet_name: str = 'SoW (Hung)', prj_id: str = "project_1", project_type: str = "Automation", credentials_path: Optional[str] = None, credentials_json: Optional[Dict] = None) -> pd.DataFrame:
    reader = sow_reader(credentials_path=credentials_path, credentials_json=credentials_json)
    df = reader.read_sow_sheet_data(sheet_url, worksheet_name)
    df_formatted = reader.format_sow_data(df, prj_id, project_type)
    return df_formatted

if __name__ == "__main__":
    credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    reader = sow_reader(credentials_path=credentials)
    sheet_url = "https://docs.google.com/spreadsheets/d/14oaI9Q5Whbbsy-uLV5ozf1VkxVJIBAnp31r-z22KD9Y"
    #print(list(reader.list_worksheets(sheet_url)))
    df = reader.read_sow_sheet_data(sheet_url, worksheet_name='SoW (Hung)')
    print(df)
    df_formatted = reader.format_sow_data(df, prj_id="project_1", project_type="Automation")
    print(df_formatted)
    df_formatted.to_csv("formatted_sow.csv", index=False)

    sheet_url_2 = "https://docs.google.com/spreadsheets/d/1GMy_MAZY9P-sJnHWXKue7kyNUtjEyWM7CIFEia9HGSQ"
    df2 = reader.read_sow_sheet_data(sheet_url_2, worksheet_name='SoW')
    df2_formatted = reader.format_sow_data(df2, prj_id="project_2", project_type="Forecasting")
    print(df2_formatted)
    df2_formatted.to_csv("formatted_sow_2.csv", index=False)