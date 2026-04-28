import json
import re
from typing import Dict, Any
import os
from google.cloud import discoveryengine_v1 as discoveryengine
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .evaluate import BaseEvaluator
from .prompts import build_evaluation_prompt
from .config import logger

class VertexEvaluator(BaseEvaluator):
    def __init__(self, model_id: str = None, project_id: str = None, location: str = None):
        """
        Initializes the Discovery Engine Evaluator.
        """
        self.project_id = project_id or os.getenv("PROJECT_ID", "project-9486ad0d-3ebc-4395-a7c")
        self.location = "us" 
        self.engine_id = "ssc-review-app_1776607831356"
        
        endpoint = f"{self.location}-discoveryengine.googleapis.com"
        client_options = {"api_endpoint": endpoint}
        
        self.client = discoveryengine.ConversationalSearchServiceClient(client_options=client_options)
        logger.info(f"Initialized Discovery Engine Evaluator at {endpoint} for project={self.project_id}, location={self.location}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ValueError, Exception)),
        before_sleep=lambda retry_state: logger.warning(f"Retrying evaluation (attempt {retry_state.attempt_number})...")
    )
    def evaluate(self, application_text: str, rubric: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """
        Grounded evaluation using Discovery Engine AnswerQuery.
        Refactored to minimize prompt stuffing and maximize Search Credit usage.
        """
        # Trim application text if it's excessively long
        if len(application_text) > 40000:
            logger.info(f"Trimming application text from {len(application_text)} to 40000 chars for focus.")
            application_text = application_text[:40000]

        serving_config = f"projects/{self.project_id}/locations/{self.location}/collections/default_collection/engines/{self.engine_id}/servingConfigs/default_serving_config"

        # LEAN SCHEMA for the prompt
        schema = {
            "applicant_id": "string",
            "overall_summary": "string",
            "ready_for_human_review": True,
            "course_checklist": [
                {
                    "module": "string", "course_code": "string", "title": "string",
                    "institution": "string", "grade": "string", "status": "string",
                    "is_satisfied": True, "note": "string"
                }
            ],
            "criteria": [
                {
                    "criterion_id": "string", "criterion_name": "string",
                    "recommended_rating": "string", "confidence": 0.95,
                    "supporting_evidence": "string", "missing_evidence": "string",
                    "needs_human_attention": False, "draft_comment": "string"
                }
            ]
        }

        # 1. BEHAVIORAL INSTRUCTIONS (Preamble)
        # We focus on the "How" and the "Output Format" here. 
        # We REMOVE the guideline text itself, as that is what the Data Store is for.
        behavioral_prompt = (
            "You are an expert SSC Accreditation Reviewer. Your goal is to provide a reliable, evidence-based assessment.\n\n"
            "### Core Logic\n"
            "1. Professional Identity: Distinguish between a Professional Statistician and other fields (Data Science/ML). Focus on study design and classical inference.\n"
            "2. Education Primacy: The course checklist is the most important component.\n"
            "3. Grounding: You MUST use the SSC guidelines and approved course lists from your Data Store to verify the courses in the application.\n"
            "4. Missing Evidence: Explicitly list required information that is not found.\n"
            "5. Uncertainty: If evidence is contradictory, set 'needs_human_attention' to true.\n\n"
            "### Output Format\n"
            f"Return ONLY a valid JSON object matching this schema: {json.dumps(schema)}"
        )

        # 2. CASE DATA (Prompt/Preamble)
        # We keep the applicant data in the preamble to avoid the 2000-char query limit
        case_data = f"### APPLICANT MATERIALS\n{application_text}\n\n### EVALUATION RUBRIC\n{json.dumps(rubric)}"
        
        preamble = f"{behavioral_prompt}\n\n{case_data}"
        
        # 3. THE SEARCH QUERY
        # We make the query descriptive of what the engine needs to "Find" in the Data Store.
        # This triggers the Search API properly.
        query_text = "Search the SSC Accreditation Guidelines and University Course Lists to evaluate if this applicant meets the educational and professional requirements for the designation."

        logger.info(f"Querying Discovery Engine with Lean Preamble (Preamble: {len(preamble)} chars)")
        
        try:
            request = discoveryengine.AnswerQueryRequest(
                serving_config=serving_config,
                query=discoveryengine.Query(text=query_text),
                answer_generation_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec(
                    ignore_adversarial_query=True,
                    include_citations=True,
                    answer_language_code="en-US",
                    model_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.ModelSpec(
                        model_version="stable"
                    ),
                    prompt_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.PromptSpec(
                        preamble=preamble
                    )
                )
            )
            
            response = self.client.answer_query(request)
            answer_text = response.answer.answer_text
            
            if not answer_text or "could not be generated" in answer_text:
                logger.error(f"Discovery Engine failed to generate summary. Raw response: {answer_text}")
                raise ValueError("AI failed to generate a summary. This often happens if the input is too complex.")

            # Clean up the response text to find JSON
            json_match = re.search(r'\{.*\}', answer_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = answer_text

            try:
                result = json.loads(json_str)
                # Ensure the required arrays exist
                if "course_checklist" not in result: result["course_checklist"] = []
                if "criteria" not in result: result["criteria"] = []
                return result
            except Exception as parse_error:
                logger.error(f"JSON Parse Error. Raw text snippet: {answer_text[:200]}")
                raise ValueError("Malformed JSON returned from AI.")

        except Exception as e:
            if isinstance(e, ValueError): raise e
            logger.error(f"❌ API Error: {e}")
            raise e
