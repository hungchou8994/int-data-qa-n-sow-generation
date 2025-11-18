# logic engine for questionnaire generation

import logging
import uuid
from datetime import datetime
from typing import List, Optional
import google.generativeai as genai
import os
import sys
import json
import time
from dotenv import load_dotenv

load_dotenv()

from .model import (
    QuestionnaireInput, QuestionnaireOutput, Question, 
    RetrievalResult, LLMPrompt, GenerationConfig
)
from .prompts import SYSTEM_PROMPT


sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from rag.bq_vector import retrieve_similar_questions

logger = logging.getLogger(__name__)


class QuestionnaireEngine:
    
    def __init__(self, google_api_key: Optional[str] = None):
        self.api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("QuestionnaireEngine initialized successfully")
        self.credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not self.credentials_path:
            logger.info("No credentials path found. Using default credentials(if it have permission) .")
    def generate_questionnaire(
        self, 
        input_data: QuestionnaireInput,
        config: Optional[GenerationConfig] = None,
        previous_questionnaire: Optional[QuestionnaireOutput] = None,
        feedback: Optional[str] = None
    ) -> tuple[QuestionnaireOutput, List[RetrievalResult]]:
        """
        Generate questionnaire with RAG-enhanced prompting
        
        Returns:
            Tuple of (questionnaire, rag_questions) - rag_questions can be reused for judge
        """
        try:
            if config is None:
                config = GenerationConfig()
            
            logger.info(f"Generating questionnaire for customer: {input_data.customer_name}")
            
            # Step 1: Retrieve similar questions
            query_content = self._build_query_content(input_data,feedback)
            retrieved_results = self._retrieve_similar_questions(query_content, config.retrieval_top_k)
            
            # Step 2: Generate questionnaire using LLM
            questionnaire = self._generate_with_llm(input_data, retrieved_results, config, previous_questionnaire, feedback)
            
            logger.info(f"Successfully generated questionnaire with {len(questionnaire.questions)} questions")
            return questionnaire, retrieved_results  # Return both for orchestrator to reuse
            
        except Exception as e:
            logger.error(f"Error generating questionnaire: {str(e)}")
            raise
    
    def _build_query_content(self, input_data: QuestionnaireInput, feedback: Optional[str] = None) -> str:
        query_parts = [
            f"Customer Name: {input_data.customer_name}",
            f"Business domain: {input_data.business_domain}",
            f"Requirements: {input_data.requirements}",
            #f"Audience: {input_data.audience}"
        ]
        
        if input_data.project_type:
            query_parts.append(f"Project type: {input_data.project_type}")
        if input_data.additional_context:
            query_parts.append(f"Additional context: {input_data.additional_context}")
        if feedback:
            query_parts.append(f"User feedback for revision: {feedback}")
            
        return ", ".join(query_parts)
    
    def _retrieve_similar_questions(self, query_content: str, top_k: int) -> List[RetrievalResult]:
        try:
            logger.info(f"Retrieving top {top_k} similar questions")
            logger.info(f"Query content: {query_content}")
            
            results = retrieve_similar_questions(
                query_content=query_content, 
                top_k=top_k,
                credentials_path=self.credentials_path
            )
            logger.info(f"Raw results from BigQuery: {len(results)} items")
            
            if not results:
                logger.warning("No results returned from BigQuery. Possible issues:")
                logger.warning("1. BigQuery authentication failed")
                logger.warning("2. Dataset/table doesn't exist or is empty")
                logger.warning("3. Embedding model not found")
                logger.warning("4. Query content not suitable for embedding")
            
            retrieval_results = []
            for i, result in enumerate(results):
                logger.info(f"Result {i+1}: {result}")
                retrieval_results.append(RetrievalResult(
                    title=result['title'],
                    section=result['section'],
                    question=result['question'],
                    similarity_score=result['similarity_score'],
                    distance=result['distance']
                ))
            
            logger.info(f"Retrieved {len(retrieval_results)} similar questions")
            return retrieval_results
            
        except Exception as e:
            logger.error(f"Error retrieving similar questions: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []
    
    def _generate_with_llm(
        self, 
        input_data: QuestionnaireInput,
        retrieved_results: List[RetrievalResult],
        config: GenerationConfig,
        previous_questionnaire: Optional[QuestionnaireOutput] = None,
        feedback: Optional[str] = None
    ) -> QuestionnaireOutput:

        prompt = self._build_llm_prompt(input_data, retrieved_results, config, previous_questionnaire, feedback)
        formatted_prompt = prompt.format_prompt()
        max_attempts = 3
        last_exception = None
        for attempt in range(max_attempts):
            try:
                logger.info(f"Generating questionnaire with Gemini LLM (attempt {attempt+1}/{max_attempts})")
                response = self.model.generate_content(
                    formatted_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=config.temperature,
                        response_mime_type="application/json",
                        response_schema={
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "questions": {
                                    "type": "array",
                                    "items": {

                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "section": {"type": "string"},
                                            "question_text": {"type": "string"},
                                            "title": {"type": "string"},
                                        },

                                        "required": ["id", "section", "question_text"]
                                    }
                                }
                            },
                            "required": ["title", "description", "questions"]
                        }
                    )
                )
                
                if not response or not getattr(response, 'text', None):
                    logger.warning(f"No response received from Gemini LLM (attempt {attempt+1}/{max_attempts})")
                    raise ValueError("No response received from Gemini LLM")
                
                response_text = response.text
                logger.info(f"LLM Response received successfully on attempt {attempt + 1}")
                questionaires = self._parse_llm_response(response_text, input_data, retrieved_results)
                if feedback:
                    questionaires.description = f"(Regenerated by AI with feedback) {questionaires.description}"
                else:
                    questionaires.description = f"(Generated by AI) {questionaires.description}"
                    
                return questionaires
            except Exception as e:
                last_exception = e
                logger.error(f"❌ Attempt {attempt} failed: {str(e)}")
                time.sleep(attempt + 1)

        logger.error(f"❌ Failed to generate questionnaire after {max_attempts} attempts: {str(last_exception)}")
        fall_back_questionnaire = self._create_fallback_questionnaire(input_data, retrieved_results)
        logger.warning(f"Using fallback questionnaire: {fall_back_questionnaire.title}")
        return fall_back_questionnaire




    def _build_llm_prompt(
        self, 
        input_data: QuestionnaireInput,
        retrieved_results: List[RetrievalResult],
        config: GenerationConfig,
        previous_questionnaire: Optional[QuestionnaireOutput] = None,
        feedback: Optional[str] = None,
        system_prompt: str = SYSTEM_PROMPT
    ) -> LLMPrompt:
        system_prompt = system_prompt.format(min_questions=config.min_questions, max_questions=config.max_questions)

        revision_context = ""
        if previous_questionnaire and feedback:
            user_prompt = (
                f"Revise the provided questionnaire based on user feedback. "
                f"The customer is {input_data.customer_name} in the {input_data.business_domain} domain. "
                f"The questionnaire must be in {input_data.language} language."
            )

            prev_questions_str = "\n".join(
                [f"- [Section: {q.section}] {q.question_text}" for q in previous_questionnaire.questions]
            )

            revision_context = f"""
                                    --- PREVIOUS QUESTIONNAIRE (for context) ---
                                    {prev_questions_str}

                                    --- USER FEEDBACK ON PREVIOUS QUESTIONNAIRE ---
                                    {feedback}
                                    --- END OF REVISION CONTEXT ---
                                """
        else:
            user_prompt = (
                f"Create a new questionnaire for {input_data.customer_name} "
                f"in the {input_data.business_domain} domain. "
                f"The questionnaire must be in {input_data.language} language."
            )

        context = f"""
                        {revision_context}
                        --- ORIGINAL PROJECT DETAILS ---
                        Customer: {input_data.customer_name}
                        Business Domain: {input_data.business_domain}
                        Requirements: {input_data.requirements}
                        Audience: {input_data.audience}
                        Project Type: {input_data.project_type or 'Not specified'}
                        Timeline: {input_data.timeline or 'Not specified'}
                        Budget Range: {input_data.budget_range or 'Not specified'}
                        Additional Context: {input_data.additional_context or 'None'}
                    """
        
        return LLMPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context=context,
            retrieved_questions=retrieved_results
        )
    
    def _parse_llm_response(
        self, 
        response_text: str,
        input_data: QuestionnaireInput,
        retrieved_results: List[RetrievalResult]
    ) -> QuestionnaireOutput:
        try:
            logger.info(f"Attempting to parse JSON from response: {response_text[:200]}...")
            try:
                data = json.loads(response_text)
                logger.info("Successfully parsed JSON as single object")
            except:
                logger.info("Direct JSON parsing failed, please check the response format")
                raise ValueError("No valid JSON found in response")
            
            questions = []
            for i, q_data in enumerate(data.get('questions', []), 1):
                question = Question(
                    id=q_data.get('id', f'q{i}'),
                    section=q_data.get('section', 'General'),
                    question_text=q_data.get('question_text', ''),
                    title=q_data.get('title')
                )
                questions.append(question)
            
            return QuestionnaireOutput(
                questionnaire_id=str(uuid.uuid4()),
                title=data.get('title', f'Questionnaire for {input_data.customer_name}'),
                description=data.get('description', 'Generated questionnaire based on requirements'),
                customer_name=input_data.customer_name,
                business_domain=input_data.business_domain,
                audience=input_data.audience,
                language=input_data.language,
                questions=questions,
                created_at=datetime.now(),
                total_questions=len(questions)
            )
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return self._create_fallback_questionnaire(input_data, retrieved_results)
    
    def _create_fallback_questionnaire(
        self, 
        input_data: QuestionnaireInput,
        retrieved_results: List[RetrievalResult]
    ) -> QuestionnaireOutput:
        """Create fallback questionnaire from retrieved results"""
        logger.info("Creating fallback questionnaire from retrieved results")
        
        questions = []
        for i, result in enumerate(retrieved_results, 1):
            question = Question(
                id=f'q{i}',
                section=result.section,
                question_text=result.question,
                title=result.title,  
                similarity_score=result.similarity_score
            )
            questions.append(question)
        
        return QuestionnaireOutput(
            questionnaire_id=str(uuid.uuid4()),
            title=f'Questionnaire for {input_data.customer_name}',
            description='Questionnaire generated from similar questions in database',
            customer_name=input_data.customer_name,
            business_domain=input_data.business_domain,
            audience=input_data.audience,
            language=input_data.language,
            questions=questions,
            created_at=datetime.now(),
            total_questions=len(questions)
        )

