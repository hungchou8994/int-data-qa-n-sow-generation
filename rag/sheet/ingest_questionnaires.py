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
from google.genai.types import EmbedContentConfig



# # Import and use bq_vector to insert data
# import sys
# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# from bq_vector import insert_questionnaire_embeddings


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
client = genai.Client(api_key=api_key)

class questionaires_reader:
    
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
    
    def get_sheet_by_url(self, sheet_url: str, worksheet_name: Optional[str] = None) -> gspread.Worksheet:

        try:
            spreadsheet = self.client.open_by_url(sheet_url)
            
            if worksheet_name:
                worksheet = spreadsheet.worksheet(worksheet_name)
            else:
                worksheet = spreadsheet.sheet1  # Get the first sheet
                
            logger.info(f"Connected to worksheet: {worksheet.title}")
            return worksheet
            
        except Exception as e:
            logger.error(f"Error when opening Google Sheet: {str(e)}")
            raise
    
    
    
    def read_sheet_data(self, worksheet: gspread.Worksheet, 
                       range_name: Optional[str] = None,
                       include_headers: bool = True) -> pd.DataFrame:
        """
        Args:
            worksheet: Worksheet object
            range_name: Range to read (e.g. 'A1:D10'), 
            include_headers: Whether to use the first row as headers
        """
        try:
            if range_name:
                values = worksheet.get(range_name)
            else:
                values = worksheet.get_all_values()
            
            if not values:
                logger.warning("No data in worksheet")
                return pd.DataFrame()
            
            if include_headers and len(values) > 1:
                df = pd.DataFrame(values[1:], columns=values[0])
            else:
                df = pd.DataFrame(values)
            
            df = df.dropna(how='all')
            
            #If the questionnaire sheets have a fixed structure, 
            #then we will hard-code the preprocessing and conversion to JSON format rather than needing to use an LLM for the conversion.
            # Here is hard-code
            """
            if 'Section' in df.columns:
                df['Section'] = df['Section'].replace('',pd.NA)
                df['Section'] = df['Section'].fillna(method ='ffill')
            """
            logger.info(f"Read {len(df)} rows of data from worksheet")
            return df
            
        except Exception as e:
            logger.error(f"Error when reading data from worksheet: {str(e)}")
            raise
    
    def get_sheet_info(self, worksheet: gspread.Worksheet) -> Dict[str, Any]:

        try:
            info = {
                'title': worksheet.title,
                'id': worksheet.id,
                'row_count': worksheet.row_count,
                'col_count': worksheet.col_count,
                'url': worksheet.url
            }
            return info
            
        except Exception as e:
            logger.error(f"Error when getting information about worksheet: {str(e)}")
            raise




def embed_questions(questions: List[str], client: genai.Client) -> List[List[float]]:
    """Embed a list of questions using Google Generative AI"""
    try:
        logger.info(f"Embedding {len(questions)} questions in batch...")
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=questions,
            config=EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT", 
                output_dimensionality=3072, 
                title="Survey Questions Batch",
            ),
        )
        
        embeddings = [embedding.values for embedding in response.embeddings]
        logger.info(f"Successfully embedded {len(embeddings)} questions")
        return embeddings
        
    except Exception as e:
        logger.error(f"Error when embedding questions: {str(e)}")
        raise

def process_questionnaire_data(questionaires: List[Dict[str, Any]], embeddings: List[List[float]]) -> List[Dict[str, Any]]:
    """Process questionnaire data and combine with embeddings"""
    processed_data = []
    
    for i, (question, embedding) in enumerate(zip(questionaires, embeddings)):
        row = {
            "id": f"question_{i}",
            "title": question.get("title", ""),
            "section": question.get("section", ""),
            "question": question.get("question", ""),
            "embedding": embedding,
            "created_at": pd.Timestamp.now().isoformat()
        }
        processed_data.append(row)
    
    logger.info(f"Processed {len(processed_data)} questionnaire items")
    return processed_data

def main():
    """Main function to process Google Sheets data and generate embeddings"""
    from prompt import extract_json_prompt
    
    # Initialize GenAI client
    genai_client = genai.Client(api_key=api_key)
    
    # Read from Google Sheets
    connector = questionaires_reader(credentials_path="D:\Cloud-ace\service_account\int-data-qa-n-sow-generation-63bb9cfd6787.json")
    sheet_url = "https://docs.google.com/spreadsheets/d/1kB2l4l3pr0NagdZlt9tGyanRhnMxf8itq16KcqgHjVY"
    worksheet = connector.get_sheet_by_url(sheet_url)

    # print(worksheet.title)
    # print(worksheet.row_values(1))
    # print(worksheet.row_values(3))

    df = connector.read_sheet_data(worksheet)



    # Convert DataFrame to string for LLM processing
    questionaire_text = df.to_string()
    
    # # Generate questionnaires using LLM
    # response = genai_client.models.generate_content(
    #     model="gemini-2.5-flash", 
    #     contents=extract_json_prompt.format(questionaire_text=questionaire_text),
    #     config = {
    #         "response_mime_type":"application/json",
    #         "response_schema": {
    #             "type": "array",
    #             "items": {
    #                 "type": "object",
    #                 "properties": {
    #                     "title": {"type": "string"},
    #                     "section": {"type": "string"},
    #                     "question": {"type": "string"},
    #                 },
    #                 "required": ["title", "section", "question"]
    #             }
    #         }
    #     }
    # )
    # print(response.text)
    # Hard code the responses for now
    response_data = """[{"title":"Project Requirements Questionnaire","section":"Project Background & Objective","question":"What are the main objectives or outcomes of this project?"},{"title":"Project Requirements Questionnaire","section":"Project Background & Objective","question":"What problems or pain points are you trying to solve?"},{"title":"Project Requirements Questionnaire","section":"Project Background & Objective","question":"What deliverables do you expect at the end of the project?"},{"title":"Project Requirements Questionnaire","section":"Project Background & Objective","question":"What would “success” look like from your perspective?"},{"title":"Project Requirements Questionnaire","section":"Process","question":"Please describe the current process or system used for this business area."},{"title":"Project Requirements Questionnaire","section":"Process","question":"Who are the key people involved in the current process?"},{"title":"Project Requirements Questionnaire","section":"Metrics & Success Criteria","question":"Do you have any baseline data or benchmarks to compare against?"},{"title":"Project Requirements Questionnaire","section":"Metrics & Success Criteria","question":"Who will be responsible for validating final outcomes?"},{"title":"Project Requirements Questionnaire","section":"Data source & Infrastructure","question":"What are the main data sources this project will depend on? E.g: template of questionaire, template of scope of work, client information"},{"title":"Project Requirements Questionnaire","section":"Data source & Infrastructure","question":"Where is the data currently stored? (e.g., on-premise, cloud, files)"},{"title":"Project Requirements Questionnaire","section":"Data source & Infrastructure","question":"What is the current level of data accessibility ?"},{"title":"Project Requirements Questionnaire","section":"Data source & Infrastructure","question":"Are there any security or compliance requirements?"},{"title":"Project Requirements Questionnaire","section":"Others","question":"What is the desired project timeline or delivery date?"},{"title":"Project Requirements Questionnaire","section":"Others","question":"Do you have an estimated budget or financial constraint?"}]"""
    questionaires = json.loads(response_data)
    
    # Extract questions for embedding
    questions = [q.get("question", "") for q in questionaires]
    
    # # Generate embeddings
    # embeddings = embed_questions(questions, genai_client)
    
    # # Process and combine data
    # processed_data = process_questionnaire_data(questionaires, embeddings)
    
    # genai_client.close()
    
    # return processed_data

if __name__ == "__main__":
    main()
    #processed_data = main()
    #logger.info(f"Total items processed: {len(processed_data)}")
    
  
    
    # # Insert data directly to BigQuery
    # success = insert_questionnaire_embeddings(
    #     embeddings_data=processed_data,
    #     credentials_path="D:\Cloud-ace\service_account\int-data-qa-n-sow-generation-63bb9cfd6787.json"
    # )
    
    # if success:
    #     logger.info("Successfully inserted data to BigQuery")
    # else:
    #     logger.error("Failed to insert data to BigQuery")