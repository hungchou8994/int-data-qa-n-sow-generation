
import logging
import uuid
import json
import time
from datetime import datetime
from typing import Optional
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

from .model import (
    ClientInformation,
    QuestionnaireAnswer,
    ProjectDetailInput,
    ProjectDetail,
    ProjectAssumptionInput,
    ProjectAssumption,
    AssumptionSection,
    ScopeOfWorkInput,
    ScopeOfWork,
    ScopeOfWorkTask,
    GenerationConfig,
    LLMPrompt
)

from .prompts import (
    PROJECT_DETAIL_SYSTEM_PROMPT,
    PROJECT_ASSUMPTION_SYSTEM_PROMPT,
    SCOPE_OF_WORK_SYSTEM_PROMPT,
    build_project_detail_context,
    build_project_assumption_context,
    build_scope_of_work_context
)

# Import from parent directoryc
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from rag.bq_vector import BigQueryVectorManager, retrieve_similar_sow_tasks


logger = logging.getLogger(__name__)


class SOWEngine:
    
    def __init__(self, google_api_key: Optional[str] = None):
        self.api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        logger.info("SOWEngine initialized successfully")
    
    def generate_project_detail(
        self,
        input_data: ProjectDetailInput,
        config: Optional[GenerationConfig] = None,
        previous_detail: Optional[ProjectDetail] = None,
        feedback: Optional[str] = None
    ) -> ProjectDetail:
        try:
            if config is None:
                config = GenerationConfig()
            
            logger.info(f"Generating project detail for customer: {input_data.client_info.customer_name}")
            
            # Build context
            client_info_dict = {
                'customer_name': input_data.client_info.customer_name,
                'business_domain': input_data.client_info.business_domain,
                'requirements': input_data.client_info.requirements,
                'audience': input_data.client_info.audience,
                'project_type': input_data.client_info.project_type,
                'budget_range': input_data.client_info.budget_range,
                'timeline': input_data.client_info.timeline,
                'additional_context': input_data.client_info.additional_context
            }
            
            questionnaire_answers_list = [
                {
                    'question_id': ans.question_id,
                    'question_text': ans.question_text,
                    'section': ans.section,
                    'answer': ans.answer
                }
                for ans in input_data.questionnaire_answers
            ]
            
            # Add feedback context if regenerating
            feedback_context = None
            previous_detail_dict = None
            if previous_detail and feedback:
                feedback_context = feedback
                previous_detail_dict = previous_detail.to_dict()
            
            context = build_project_detail_context(
                client_info_dict,
                questionnaire_answers_list,
                feedback_context,
                previous_detail_dict
            )
            
            # Create prompt
            if previous_detail and feedback:
                user_prompt = f"""
Based on the provided client information, questionnaire responses, and user feedback,
please REVISE the project details.

Previous project detail is provided for reference. Apply the user's feedback to improve it.

Generate the project details in {input_data.client_info.language} language.
"""
            else:
                user_prompt = f"""
Based on the provided client information and questionnaire responses,
please generate sharp and concise PROJECT DETAILS.

Generate the project details in {input_data.client_info.language} language.
"""
            
            prompt = LLMPrompt(
                system_prompt=PROJECT_DETAIL_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                context=context
            )
            
            # Generate with LLM
            project_detail = self._generate_project_detail_with_llm(
                prompt,
                input_data.client_info,
                config,
                previous_detail
            )
            
            logger.info(f"Successfully generated project detail for {input_data.client_info.customer_name}")
            return project_detail
            
        except Exception as e:
            logger.error(f"Error generating project detail: {str(e)}")
            raise
    
    def generate_project_assumption(
        self,
        input_data: ProjectAssumptionInput,
        config: Optional[GenerationConfig] = None,
        previous_assumption: Optional[ProjectAssumption] = None,
        feedback: Optional[str] = None
    ) -> ProjectAssumption:
        try:
            if config is None:
                config = GenerationConfig()
            
            logger.info(f"Generating project assumptions for customer: {input_data.client_info.customer_name}")
            
            # Build context
            client_info_dict = {
                'customer_name': input_data.client_info.customer_name,
                'business_domain': input_data.client_info.business_domain,
                'project_type': input_data.client_info.project_type,
                'budget_range': input_data.client_info.budget_range,
                'timeline': input_data.client_info.timeline
            }
            
            questionnaire_answers_list = [
                {
                    'question_id': ans.question_id,
                    'question_text': ans.question_text,
                    'section': ans.section,
                    'answer': ans.answer
                }
                for ans in input_data.questionnaire_answers
            ]
            
            project_detail_dict = input_data.project_detail.to_dict()
            
            # Add feedback context if regenerating
            feedback_context = None
            previous_assumption_dict = None
            if previous_assumption and feedback:
                feedback_context = feedback
                previous_assumption_dict = previous_assumption.to_dict()
            
            context = build_project_assumption_context(
                client_info_dict,
                questionnaire_answers_list,
                project_detail_dict,
                feedback_context,
                previous_assumption_dict
            )
            
            # Create prompt
            if previous_assumption and feedback:
                user_prompt = f"""
Based on the provided client information, questionnaire responses, project details, and user feedback,
please REVISE the project assumptions.

Previous project assumptions are provided for reference. Apply the user's feedback to improve them.

Generate the project assumptions in {input_data.client_info.language} language.
"""
            else:
                user_prompt = f"""
Based on the provided client information, questionnaire responses, and project details,
please generate comprehensive PROJECT ASSUMPTIONS.

Generate the project assumptions in {input_data.client_info.language} language.
"""
            
            prompt = LLMPrompt(
                system_prompt=PROJECT_ASSUMPTION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                context=context
            )
            
            # Generate with LLM
            project_assumption = self._generate_project_assumption_with_llm(
                prompt,
                input_data.client_info,
                config,
                previous_assumption
            )
            
            logger.info(f"Successfully generated project assumptions for {input_data.client_info.customer_name}")
            return project_assumption
            
        except Exception as e:
            logger.error(f"Error generating project assumptions: {str(e)}")
            raise
    
    def _generate_project_detail_with_llm(
        self,
        prompt: LLMPrompt,
        client_info: ClientInformation,
        config: GenerationConfig,
        previous_detail: Optional[ProjectDetail] = None
    ) -> ProjectDetail:
        
        formatted_prompt = prompt.format_prompt()
        max_attempts = config.max_retries
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Generating project detail with Gemini LLM (attempt {attempt+1}/{max_attempts})")
                
                response = self.model.generate_content(
                    formatted_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=config.temperature,
                        response_mime_type="application/json",
                        response_schema={
                            "type": "object",
                            "properties": {
                                "overview": {"type": "string"},
                                "key_features": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["overview", "key_features"]
                        }
                    )
                )
                
                if not response or not getattr(response, 'text', None):
                    logger.warning(f"No response received from Gemini LLM (attempt {attempt+1}/{max_attempts})")
                    raise ValueError("No response received from Gemini LLM")
                
                response_text = response.text
                logger.info(f"LLM Response received successfully on attempt {attempt + 1}")
                
                # Parse response
                project_detail = self._parse_project_detail_response(
                    response_text,
                    client_info
                )
                
                return project_detail
                
            except Exception as e:
                last_exception = e
                logger.error(f" Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_attempts - 1:
                    time.sleep(attempt + 1)
        
        logger.error(f"Failed to generate project detail after {max_attempts} attempts: {str(last_exception)}")
        raise Exception(f"Failed to generate project detail: {str(last_exception)}")
    
    def _generate_project_assumption_with_llm(
        self,
        prompt: LLMPrompt,
        client_info: ClientInformation,
        config: GenerationConfig,
        previous_assumption: Optional[ProjectAssumption] = None
    ) -> ProjectAssumption:
        
        formatted_prompt = prompt.format_prompt()
        max_attempts = config.max_retries
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Generating project assumptions with Gemini LLM (attempt {attempt+1}/{max_attempts})")
                
                response = self.model.generate_content(
                    formatted_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=config.temperature,
                        response_mime_type="application/json",
                        response_schema={
                            "type": "object",
                            "properties": {
                                "assumptions": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "section": {"type": "string"},
                                            "points": {
                                                "type": "array",
                                                "items": {"type": "string"}
                                            }
                                        },
                                        "required": ["section", "points"]
                                    }
                                }
                            },
                            "required": ["assumptions"]
                        }
                    )
                )
                
                if not response or not getattr(response, 'text', None):
                    logger.warning(f"No response received from Gemini LLM (attempt {attempt+1}/{max_attempts})")
                    raise ValueError("No response received from Gemini LLM")
                
                response_text = response.text
                logger.info(f"LLM Response received successfully on attempt {attempt + 1}")
                
                # Parse response
                project_assumption = self._parse_project_assumption_response(
                    response_text,
                    client_info
                )
                
                return project_assumption
                
            except Exception as e:
                last_exception = e
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_attempts - 1:
                    time.sleep(attempt + 1)
        
        logger.error(f"Failed to generate project assumptions after {max_attempts} attempts: {str(last_exception)}")
        raise Exception(f"Failed to generate project assumptions: {str(last_exception)}")
    
    def _parse_project_detail_response(
        self,
        response_text: str,
        client_info: ClientInformation
    ) -> ProjectDetail:
        """Parse LLM response into ProjectDetail object"""
        try:
            logger.info(f"Parsing project detail response...")
            data = json.loads(response_text)
            
            return ProjectDetail(
                detail_id=str(uuid.uuid4()),
                customer_name=client_info.customer_name,
                business_domain=client_info.business_domain,
                overview=data.get('overview', ''),
                key_features=data.get('key_features', []),
                created_at=datetime.now(),
                language=client_info.language
            )
            
        except Exception as e:
            logger.error(f"Error parsing project detail response: {str(e)}")
            raise
    
    def _parse_project_assumption_response(
        self,
        response_text: str,
        client_info: ClientInformation
    ) -> ProjectAssumption:
        try:
            logger.info(f"Parsing project assumption response...")
            data = json.loads(response_text)
            
            # Parse assumption sections
            assumption_sections = []
            for section_data in data.get('assumptions', []):
                assumption_sections.append(
                    AssumptionSection(
                        section=section_data.get('section', ''),
                        points=section_data.get('points', [])
                    )
                )
            
            return ProjectAssumption(
                assumption_id=str(uuid.uuid4()),
                customer_name=client_info.customer_name,
                business_domain=client_info.business_domain,
                assumptions=assumption_sections,
                created_at=datetime.now(),
                language=client_info.language
            )
            
        except Exception as e:
            logger.error(f"Error parsing project assumption response: {str(e)}")
            raise
    
    def generate_scope_of_work(
        self,
        input_data: ScopeOfWorkInput,
        config: Optional[GenerationConfig] = None,
        previous_sow: Optional[ScopeOfWork] = None,
        feedback: Optional[str] = None,
        top_k: int = 20  # RAG top_k parameter
    ) -> ScopeOfWork:
        try:
            if config is None:
                config = GenerationConfig()
            
            logger.info(f" Generating Scope of Work for {input_data.client_info.customer_name}")
            
            # Step 1: Retrieve similar tasks using RAG (skip if top_k=0)
            rag_tasks = []
            if top_k > 0:
                logger.info(f"Retrieving top {top_k} similar tasks from past projects...")
                query_text = self._build_rag_query(
                    input_data.client_info,
                    input_data.project_detail,
                    input_data.project_assumption
                )
                
                rag_tasks = retrieve_similar_sow_tasks(
                    query_content=query_text,
                    top_k=top_k,
                    credentials_path=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                )
                
                logger.info(f" Retrieved {len(rag_tasks)} similar tasks (RAG)")
            else:
                logger.info("⏭️ Skipping RAG retrieval (top_k=0, generate without RAG context)")
            
            # Step 2: Build context
            client_info_dict = {
                'customer_name': input_data.client_info.customer_name,
                'business_domain': input_data.client_info.business_domain,
                'project_type': input_data.client_info.project_type,
                'timeline': input_data.client_info.timeline
            }
            
            questionnaire_answers_list = [
                {
                    'question_id': ans.question_id,
                    'question_text': ans.question_text,
                    'section': ans.section,
                    'answer': ans.answer
                }
                for ans in input_data.questionnaire_answers
            ]
            
            project_detail_dict = input_data.project_detail.to_dict()
            project_assumption_dict = input_data.project_assumption.to_dict()
            
            # Add feedback context if regenerating
            feedback_context = None
            previous_sow_dict = None
            if previous_sow and feedback:
                feedback_context = f"Previous version had {previous_sow.total_tasks} tasks with {previous_sow.total_man_days} man-days. User feedback: {feedback}"
                previous_sow_dict = previous_sow.to_dict()
            
            context = build_scope_of_work_context(
                client_info_dict,
                questionnaire_answers_list,
                project_detail_dict,
                project_assumption_dict,
                rag_tasks,
                feedback_context,
                previous_sow_dict
            )
            
            # Step 3: Create prompt
            if previous_sow and feedback:
                user_prompt = f"""Please REGENERATE the Scope of Work based on the feedback.

Previous Context: {json.dumps(previous_sow.to_dict(), indent=2)}

User Feedback: {feedback}

Generate an IMPROVED version addressing the feedback. Output in JSON format."""
            else:
                user_prompt = """Generate a comprehensive Scope of Work (task breakdown) based on the provided information.

IMPORTANT:
1. Adapt RAG tasks to this specific project (don't copy blindly)
2. Ensure consistency with Project Assumptions
3. Be specific and actionable
4. Provide realistic man-day estimates

Output in JSON format."""
            
            prompt = LLMPrompt(
                system_prompt=SCOPE_OF_WORK_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                context=context
            )
            
            # Step 4: Generate with LLM
            scope_of_work = self._generate_sow_with_llm(
                prompt,
                input_data.client_info,
                config,
                rag_tasks
            )
            
            logger.info(f"✅ Generated Scope of Work: {scope_of_work.total_tasks} tasks, {scope_of_work.total_man_days} man-days")
            
            # Return both SoW and rag_tasks (for judge to use, avoid duplicate RAG query)
            return scope_of_work, rag_tasks
            
        except Exception as e:
            logger.error(f"❌ Error generating scope of work: {str(e)}")
            raise
    
    def _build_rag_query(
        self,
        client_info: ClientInformation,
        project_detail: ProjectDetail,
        project_assumption: ProjectAssumption
    ) -> str:
        """Build query for RAG retrieval"""
        parts = [
            f"Project type: {client_info.project_type}",
            f"Business domain: {client_info.business_domain}",
            f"Overview: {project_detail.overview}",
        ]
        
        # Add key features
        for feature in project_detail.key_features:
            parts.append(f"Feature: {feature}")
        
        # Add key assumptions
        for section in project_assumption.assumptions:
            for point in section.points:
                parts.append(f"Requirement: {point}")

        return " ".join(parts)
    
    def _generate_sow_with_llm(
        self,
        prompt: LLMPrompt,
        client_info: ClientInformation,
        config: GenerationConfig,
        rag_tasks: list
    ) -> ScopeOfWork:
        formatted_prompt = prompt.format_prompt()
        max_attempts = config.max_retries
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                logger.info(f" Attempt {attempt + 1}/{max_attempts} to generate SoW...")
                
                response = self.model.generate_content(
                    formatted_prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=config.temperature,
                        response_mime_type="application/json",
                        response_schema={
                            "type": "object",
                            "properties": {
                                "tasks": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "task_category": {"type": "string"},
                                            "task_title": {"type": "string"},
                                            "content": {"type": "string"},
                                            "man_days": {"type": "number"}
                                        },
                                        "required": ["task_category", "task_title", "content", "man_days"]
                                    }
                                }
                            },
                            "required": ["tasks"]
                        }
                    )
                )
                
                logger.info("✅ LLM response received")
                
                # Parse response (detailed logging moved to _parse_sow_response)
                sow = self._parse_sow_response(
                    response.text,
                    client_info,
                    rag_tasks
                )
                
                logger.info(f"✅ SoW parsed successfully: {sow.total_tasks} tasks, {sow.total_man_days} man-days")
                return sow
                
            except Exception as e:
                last_exception = e
                logger.warning(f" Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_attempts - 1:
                    time.sleep(2)
        
        logger.error(f"Failed to generate SoW after {max_attempts} attempts: {str(last_exception)}")
        raise Exception(f"Failed to generate scope of work: {str(last_exception)}")
    
    def _parse_sow_response(
        self,
        response_text: str,
        client_info: ClientInformation,
        rag_tasks: list
    ) -> ScopeOfWork:
        try:
            logger.info("📄 Parsing SoW response...")
            logger.info(f"📏 Response length: {len(response_text)} characters")
            logger.info(f"🔍 First 500 chars:\n{response_text[:500]}...")
            
            # Clean response text (remove potential markdown code blocks)
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Parse JSON with better error reporting
            try:
                data = json.loads(cleaned_text)
            except json.JSONDecodeError as json_err:
                logger.error(f"❌ JSON decode error at line {json_err.lineno}, col {json_err.colno}: {json_err.msg}")
                logger.error(f"📄 Problematic section:\n{cleaned_text[max(0, json_err.pos-100):json_err.pos+100]}")
                raise ValueError(f"Invalid JSON at line {json_err.lineno}: {json_err.msg}")
            
            # Validate structure
            if not isinstance(data, dict):
                raise ValueError(f"Response must be JSON object, got {type(data).__name__}")
            if 'tasks' not in data:
                raise ValueError(f"Response missing 'tasks' field. Available fields: {list(data.keys())}")
            if not isinstance(data['tasks'], list):
                raise ValueError(f"'tasks' must be array, got {type(data['tasks']).__name__}")
            
            logger.info(f"✅ Found {len(data['tasks'])} tasks in response")
            
            # Debug: Check first task content formatting
            if data['tasks']:
                first_task = data['tasks'][0]
                logger.info(f"🔍 First task content (raw): {repr(first_task.get('content', ''))[:200]}")
            
            # Parse tasks
            tasks = []
            rag_task_titles = {task['task_title'] for task in rag_tasks}
            
            for i, task_data in enumerate(data.get('tasks', [])):
                try:
                    # Validate required fields
                    required_fields = ['task_category', 'task_title', 'content', 'man_days']
                    missing_fields = [f for f in required_fields if f not in task_data]
                    if missing_fields:
                        logger.warning(f"⚠️ Task {i+1} missing fields {missing_fields}, skipping")
                        continue
                    
                    task_title = task_data.get('task_title', '')
                    task_content = task_data.get('content', '')
                    
                    # Auto-format content: Add line breaks between sentences for readability
                    # Split by ". " and rejoin with ". \n\n" for paragraph breaks
                    if task_content and '. ' in task_content:
                        sentences = task_content.split('. ')
                        # Add period back and join with double newline
                        formatted_content = '.\n\n'.join(sentences)
                        # Clean up: if last sentence already has period, don't double it
                        if not formatted_content.endswith('.'):
                            formatted_content = formatted_content.rstrip() + '.'
                    else:
                        formatted_content = task_content
                    
                    # Determine if task is from RAG or generated
                    source = "rag" if task_title in rag_task_titles else "generated"
                    similarity_score = None
                    
                    # Find similarity score if from RAG
                    if source == "rag":
                        for rag_task in rag_tasks:
                            if rag_task['task_title'] == task_title:
                                similarity_score = rag_task.get('similarity_score')
                                break
                    
                    tasks.append(
                        ScopeOfWorkTask(
                            task_category=task_data.get('task_category', 'General'),
                            task_title=task_title,
                            content=formatted_content,  # Use formatted content with line breaks
                            man_days=float(task_data.get('man_days', 1.0)),
                            source=source,
                            similarity_score=similarity_score
                        )
                    )
                except Exception as task_err:
                    logger.warning(f"⚠️ Error parsing task {i+1}: {task_err}, skipping")
                    continue
            
            if not tasks:
                raise ValueError(f"No valid tasks parsed from {len(data.get('tasks', []))} raw tasks")
            
            logger.info(f"✅ Successfully parsed {len(tasks)} valid tasks")
            
            # Calculate totals
            total_man_days = sum(task.man_days for task in tasks)
            total_tasks = len(tasks)
            
            return ScopeOfWork(
                sow_id=str(uuid.uuid4()),
                customer_name=client_info.customer_name,
                business_domain=client_info.business_domain,
                project_type=client_info.project_type or "General",
                tasks=tasks,
                total_man_days=total_man_days,
                total_tasks=total_tasks,
                created_at=datetime.now(),
                language=client_info.language
            )
            
        except Exception as e:
            logger.error(f"❌ Error parsing SoW response: {str(e)}")
            logger.error(f"📄 Full response:\n{response_text}")
            raise
