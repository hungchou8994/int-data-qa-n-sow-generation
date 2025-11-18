#interact with bigquery
import os
import sys
import json
import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from google.cloud import bigquery
from google.oauth2.service_account import Credentials
from google.auth import default

# Import with absolute path handling
try:
    from sheet.ingest_sows import read_format_sow
except ImportError:
    # Try relative import if running from different location
    from .sheet.ingest_sows import read_format_sow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BigQueryVectorManager:
    
    def __init__(self, credentials_path: Optional[str] = None, credentials_json: Optional[Dict] = None):
 
        self.client = None
        self.project_id = None
        if not credentials_path:
            self.credentials_path = "D:\Cloud-ace\service_account\int-data-qa-n-sow-generation-63bb9cfd6787.json"
            logger.info(f"Using default credentials path: {self.credentials_path}")
        else:
            self.credentials_path = credentials_path
            logger.info(f"Using credentials path: {self.credentials_path}")
        self._authenticate(self.credentials_path, credentials_json)
    
    def _authenticate(self, credentials_path: Optional[str], credentials_json: Optional[Dict]):
        try:
            creds = None
            
            if credentials_json:
                creds = Credentials.from_service_account_info(
                    credentials_json, 
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                logger.info("Using credentials from dictionary")
            elif credentials_path and os.path.exists(credentials_path):
                creds = Credentials.from_service_account_file(
                    credentials_path, 
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                logger.info(f"Using credentials from file: {credentials_path}")
            else:
                try:
                    creds, project = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
                    logger.info(f"Using Application Default Credentials for project: {project}")
                except Exception as adc_error:
                    raise ValueError(
                        "Cannot find Google credentials. Please provide credentials_path, "
                        "credentials_json, or set up Application Default Credentials."
                    )
            
            self.client = bigquery.Client(credentials=creds)
            self.project_id = self.client.project
            logger.info(f"Connected to BigQuery project: {self.project_id}")
            
        except Exception as e:
            logger.error(f"Error authenticating with BigQuery: {str(e)}")
            raise
    
    def insert_data(self, dataset_id: str, table_id: str, data: List[Dict[str, Any]]) -> bool:
      
        try:
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            table = bigquery.Table(table_ref)
            
            # Insert data directly
            errors = self.client.insert_rows_json(table, data)
            
            if errors:
                logger.error(f"Errors inserting data: {errors}")
                return False
            else:
                logger.info(f"Successfully inserted {len(data)} rows into {table_ref}")
                return True
                
        except Exception as e:
            logger.error(f"Error inserting data into {dataset_id}.{table_id}: {str(e)}")
            return False

    def insert_sow_raw_data(self, dataset_id: str, table_id: str, sheet_url: str, worksheet_name: str, prj_id: str, project_type: str) -> bool:

        try:
            df = read_format_sow(sheet_url, worksheet_name, prj_id, project_type, self.credentials_path)
            
            if df is None or df.empty:
                logger.warning("No data to insert")
                return True 
            
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"

            try:
                table = self.client.get_table(table_ref)
                bq_schema = table.schema
                logger.info(f"Retrieved schema from destination table: {table_ref}")
            except Exception as e:
                logger.error(f"Error: Table '{table_ref}' not found in BigQuery.")
                logger.error("You must create the table (e.g., 'sow_tasks_raw_content') in the BQ Console FIRST.")
                logger.error(f"Detailed error: {e}")
                return False

            job_config = bigquery.LoadJobConfig(
                schema=bq_schema,
                write_disposition="WRITE_APPEND",
            )

            logger.info(f"Uploading {len(df)} rows (tasks) to {table_ref}...")
            job = self.client.load_table_from_dataframe(df, table_ref, job_config=job_config)
            job.result()

            logger.info(f"Upload to BigQuery successful. Added {job.output_rows} rows to {table_ref}")
            return True

        except Exception as e:
            logger.error(f"Error uploading SoW raw data to {dataset_id}.{table_id}: {str(e)}")
            if hasattr(e, 'errors'):
                for error in e.errors:
                    logger.error(f"BQ Error Detail: {error['message']}")
            return False

   

    def retrieve_similar_questions(
        self, 
        query_content: str, 
        top_k: int = 10,
        dataset_id: str = "qa_sow_dataset",
        embedding_model: str = "gemini_embedding_model",
        embeddings_table: str = "embeddings_questions"
    ) -> List[Dict[str, Any]]:
       
        try:
            # Build the SQL query
            sql_query = f"""
            WITH query_embedding AS (
              SELECT
                ml_generate_embedding_result AS embedding
              FROM
                ML.GENERATE_EMBEDDING(
                  MODEL `{self.project_id}.{dataset_id}.{embedding_model}`,
                  (SELECT @query_content AS content),
                  STRUCT(TRUE AS flatten_json_output, 'RETRIEVAL_QUERY' AS task_type)
                )
            ),

            similarity_scores AS (
              SELECT
                e.title,
                e.section,
                e.question,
                ML.DISTANCE(e.embedding, q.embedding, 'COSINE') AS distance,
                1 - ML.DISTANCE(e.embedding, q.embedding, 'COSINE') AS similarity_score
              FROM
                `{self.project_id}.{dataset_id}.{embeddings_table}` e,
                query_embedding q
            )

            SELECT
              title,
              section,
              question,
              similarity_score,
              distance
            FROM
              similarity_scores
            ORDER BY
              similarity_score DESC
            LIMIT @top_k
            """
            
            # Configure query parameters
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_content", "STRING", query_content),
                    bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
                ]
            )
            
            # Execute query
            logger.info(f"Executing similarity search for query: '{query_content[:100]}...'")
            logger.info(f"SQL Query: {sql_query}")
            
            query_job = self.client.query(sql_query, job_config=job_config)
            logger.info(f"Query job created: {query_job.job_id}")
            
            results = query_job.result()
            logger.info(f"Query job completed successfully")
            
            # Convert results to list of dictionaries
            similar_questions = []
            row_count = 0
            for row in results:
                row_count += 1
                logger.info(f"Processing row {row_count}: title={row.title}, section={row.section}, score={row.similarity_score}")
                similar_questions.append({
                    'title': row.title,
                    'section': row.section,
                    'question': row.question,
                    'similarity_score': float(row.similarity_score),
                    'distance': float(row.distance)
                })
            
            logger.info(f"Retrieved {len(similar_questions)} similar questions from {row_count} rows")
            
            if len(similar_questions) == 0:
                logger.warning("No similar questions found. Checking possible issues:")
                logger.warning(f"1. Table `{self.project_id}.{dataset_id}.{embeddings_table}` might be empty")
                logger.warning(f"2. Embedding model `{self.project_id}.{dataset_id}.{embedding_model}` might not exist")
                logger.warning("3. Query content might not generate valid embeddings")
                
            return similar_questions
            
        except Exception as e:
            logger.error(f"Error retrieving similar questions: {str(e)}")
            return []

    def retrieve_similar_sow_tasks(
        self, 
        query_content: str, 
        top_k: int = 20,
        dataset_id: str = "qa_sow_dataset", 
        embedding_model: str = "gemini_embedding_model", 
        embeddings_table: str = "sow_tasks_embedded" 
    ) -> List[Dict[str, Any]]:
 
        try:
            sql_query = f"""
            WITH query_embedding AS (
              SELECT
                ml_generate_embedding_result AS embedding
              FROM
                ML.GENERATE_EMBEDDING(
                  MODEL `{self.project_id}.{dataset_id}.{embedding_model}`,
                  (SELECT @query_content AS content),
                  STRUCT(TRUE AS flatten_json_output, 'RETRIEVAL_QUERY' AS task_type)
                )
            ),

            similarity_scores AS (
              SELECT
                e.prj_id,
                e.project_type,
                e.task_category,
                e.task_title,
                e.content,
                e.man_days,
                ML.DISTANCE(e.embedding, q.embedding, 'COSINE') AS distance,
                1 - ML.DISTANCE(e.embedding, q.embedding, 'COSINE') AS similarity_score
              FROM
                `{self.project_id}.{dataset_id}.{embeddings_table}` e, 
                query_embedding q
            )

            SELECT
              prj_id,
              project_type,
              task_category,
              task_title,
              content,
              man_days,
              similarity_score,
              distance
            FROM
              similarity_scores
            ORDER BY
              similarity_score DESC
            LIMIT @top_k
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_content", "STRING", query_content),
                    bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
                ]
            )
            
            logger.info(f"Executing SOW similarity search for query: '{query_content[:100]}...'")
            logger.info(f"SQL Query: {sql_query}")
            
            query_job = self.client.query(sql_query, job_config=job_config)
            logger.info(f"Query job created: {query_job.job_id}")
            
            results = query_job.result()
            logger.info(f"Query job completed successfully")
            
            similar_tasks = [] 
            row_count = 0
            for row in results:
                row_count += 1
                similar_tasks.append({
                    'prj_id': row.prj_id,
                    'project_type': row.project_type,
                    'task_category': row.task_category,
                    'task_title': row.task_title,
                    'content': row.content,
                    'man_days': float(row.man_days) if row.man_days is not None else None,
                    'similarity_score': float(row.similarity_score),
                    'distance': float(row.distance)
                })
            
            logger.info(f"Retrieved {len(similar_tasks)} similar tasks from {row_count} rows")
            
            if len(similar_tasks) == 0:
                logger.warning("No similar tasks found. Checking possible issues:")
                logger.warning(f"1. Table `{self.project_id}.{dataset_id}.{embeddings_table}` might be empty")
                logger.warning(f"2. Embedding model `{self.project_id}.{dataset_id}.{embedding_model}` might not exist")
            
            return similar_tasks
            
        except Exception as e:
            logger.error(f"Error retrieving similar SOW tasks: {str(e)}")
            return []


def insert_questionnaire_embeddings(
    embeddings_data: List[Dict[str, Any]], 
    credentials_path: str,
    dataset_id: str = "qa_sow_dataset",
    table_id: str = "questionaires"
) -> bool:
 
    try:
        # Initialize BigQuery inserter
        inserter = BigQueryVectorManager(credentials_path=credentials_path)
        
        # Insert data directly
        success = inserter.insert_data(dataset_id, table_id, embeddings_data)
        
        return success
        
    except Exception as e:
        logger.error(f"Error in insert_questionnaire_embeddings: {str(e)}")
        return False




def retrieve_similar_questions(
    query_content: str,
    top_k: int = 10,
    dataset_id: str = "qa_sow_dataset",
    embedding_model: str = "gemini_embedding_model",
    embeddings_table: str = "embeddings_questions",
    credentials_path: Optional[str] = None
) -> List[Dict[str, Any]]:
 
    try:
        logger.info(f"Creating BigQueryVectorManager...")
        bq_manager = BigQueryVectorManager(credentials_path=credentials_path)
        
        if not bq_manager.client:
            logger.error("BigQuery client not initialized")
            return []
            
        logger.info(f"BigQuery project: {bq_manager.project_id}")
        logger.info(f"Dataset: {dataset_id}, Table: {embeddings_table}, Model: {embedding_model}")
        
        return bq_manager.retrieve_similar_questions(
            query_content=query_content,
            top_k=top_k,
            dataset_id=dataset_id,
            embedding_model=embedding_model,
            embeddings_table=embeddings_table
        )
    except Exception as e:
        logger.error(f"Error retrieving similar questions: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return []
    
def retrieve_similar_sow_tasks(
    query_content: str,
    top_k: int = 10, 
    dataset_id: str = "qa_sow_dataset",
    embedding_model: str = "gemini_embedding_model",
    embeddings_table: str = "sow_tasks_embedded",
    credentials_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    try:
        bq_manager = BigQueryVectorManager(credentials_path=credentials_path)
        
        if not bq_manager.client:
            logger.error("BigQuery client not initialized")
            return []
            
        logger.info(f"BigQuery project: {bq_manager.project_id}")
        logger.info(f"Dataset: {dataset_id}, Table: {embeddings_table}, Model: {embedding_model}")
        
        return bq_manager.retrieve_similar_sow_tasks(
            query_content=query_content,
            top_k=top_k,
            dataset_id=dataset_id,
            embedding_model=embedding_model,
            embeddings_table=embeddings_table
        )
    except Exception as e:
        logger.error(f"Error retrieving similar SOW tasks: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return []






def test_bigquery_functions():
    
    print("=" * 60)
    print("TESTING BIGQUERY VECTOR FUNCTIONS")
    print("=" * 60)
    
    # Test 1: Initialize BigQueryVectorManager
    print("\n1. Testing BigQueryVectorManager initialization...")
    try:
        bq_manager = BigQueryVectorManager()
        print(f"   SUCCESS: BigQuery Manager initialized successfully")
        print(f"   Project: {bq_manager.project_id}")
        
        if hasattr(bq_manager, 'credentials') and hasattr(bq_manager.credentials, 'service_account_email'):
            print(f"   SUCCESS: Using SERVICE ACCOUNT: {bq_manager.credentials.service_account_email}")
        else:
            print(f"   WARNING: Using USER ACCOUNT (may have permission issues)")
            
    except Exception as e:
        print(f"   ERROR: Failed to initialize: {str(e)}")
        return False
    
    # Test 2: Test simple BigQuery connection
    print("\n2. Testing basic BigQuery connection...")
    try:
        query = "SELECT 1 as test_value"
        query_job = bq_manager.client.query(query)
        results = query_job.result()
        
        for row in results:
            print(f"   SUCCESS: Basic query works: {row.test_value}")
            
    except Exception as e:
        print(f"   ERROR: Basic query failed: {str(e)}")
        return False
    
    # Test 3: Check if dataset and table exist
    print("\n3. Checking dataset and table...")
    dataset_id = "qa_sow_dataset"
    table_id = "embeddings_questions"
    
    try:
        # Check dataset
        dataset_ref = bq_manager.client.dataset(dataset_id)
        dataset = bq_manager.client.get_dataset(dataset_ref)
        print(f"   SUCCESS: Dataset '{dataset_id}' exists")
        
        # Check table
        table_ref = dataset_ref.table(table_id)
        table = bq_manager.client.get_table(table_ref)
        print(f"   SUCCESS: Table '{table_id}' exists with {table.num_rows} rows")
        
    except Exception as e:
        print(f"   ERROR: Dataset/table check failed: {str(e)}")
        return False
    
    # Test 4: Test retrieve_similar_questions function
    print("\n4. Testing retrieve_similar_questions...")
    test_queries = [
        "Customer management system with CRM features",
        "Data analytics dashboard for business intelligence", 
        "Mobile application for e-commerce platform"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n   Test Query {i}: '{query}'")
        try:
            results = retrieve_similar_questions(
                query_content=query,
                top_k=3
            )
            
            print(f"   SUCCESS: Retrieved {len(results)} similar questions")
            
            for j, result in enumerate(results, 1):
                print(f"      {j}. [{result['section']}] {result['title']}")
                print(f"         Score: {result['similarity_score']:.3f}")
                print(f"         Question: {result['question'][:80]}...")
                
        except Exception as e:
            print(f"   ERROR: Query {i} failed: {str(e)}")
            if "403" in str(e) and "connection" in str(e).lower():
                print(f"   INFO: This is the connection permission error we've been seeing")
            continue
    
    # Test 5: Test insert function (optional - only if you want to test inserting)
    print("\n5. Testing insert functionality (dry run)...")
    try:
        # Sample data for testing (don't actually insert)
        sample_data = [
            {
                "title": "Test Question 1",
                "section": "Test Section",
                "question": "This is a test question for validation",
                "embedding": [0.1] * 768  # Dummy embedding
            }
        ]
        
        print(f"   SUCCESS: Sample data prepared: {len(sample_data)} items")
        print(f"   INFO: Skipping actual insert to avoid data pollution")
        
    except Exception as e:
        print(f"   ERROR: Insert test preparation failed: {str(e)}")
    
    # Test 6: Summary
    print(f"\n6. Test Summary:")
    print(f"   - BigQuery connection: SUCCESS")
    print(f"   - Dataset/table access: SUCCESS") 
    print(f"   - Basic queries: SUCCESS")
    print(f"   - Retrieve function: Check individual results above")
    print(f"   - Main issue: Connection permissions for ML.GENERATE_EMBEDDING")
    
    print("\n" + "=" * 60)
    print("CONCLUSION:")
    print("   The BigQuery setup works for basic operations.")
    print("   The ML embedding issue is specifically about connection permissions.")
    print("   Service account should resolve this issue.")
    print("=" * 60)
    
    return True


def main():
    # sow_loader = BigQueryVectorManager()
    # sow_loader.insert_sow_raw_data(
    #     dataset_id="qa_sow_dataset",
    #     table_id="sow_tasks_raw",
    #     sheet_url="https://docs.google.com/spreadsheets/d/14oaI9Q5Whbbsy-uLV5ozf1VkxVJIBAnp31r-z22KD9Y",
    #     worksheet_name="SoW (Hung)",    
    #     prj_id="project_1",
    #     project_type="Automation"
    # )
    # sow_loader.insert_sow_raw_data(
    #     dataset_id="qa_sow_dataset",
    #     table_id="sow_tasks_raw",
    #     sheet_url="https://docs.google.com/spreadsheets/d/1GMy_MAZY9P-sJnHWXKue7kyNUtjEyWM7CIFEia9HGSQ",
    #     worksheet_name="SoW",    
    #     prj_id="project_2",
    #     project_type="Forecasting"
    # )

     
    similar_tasks = retrieve_similar_sow_tasks(
        query_content="Develop a customer relationship management system with analytics features",
        top_k=5,
        credentials_path="D:\Cloud-ace\service_account\int-data-qa-n-sow-generation-63bb9cfd6787.json"
    )
    print("Similar SOW Tasks:")

    for i, task in enumerate(similar_tasks, 1): 
        print(f"{i}. [{task['task_category']}] {task['task_title']}")
        print(f"   Score: {task['similarity_score']:.3f}")
        print(f"   Content: {task['content'][:100]}...")

if __name__ == "__main__":
    main()

    