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
        Grounded evaluation using Discovery Engine AnswerQuery with automatic retries.
        """
        # Trim application text if it's excessively long to improve AI focus and reduce summary failures
        # 140k characters is too large for AnswerQuery summary generation
        if len(application_text) > 40000:
            logger.info(f"Trimming application text from {len(application_text)} to 40000 chars.")
            application_text = application_text[:40000]

        serving_config = f"projects/{self.project_id}/locations/{self.location}/collections/default_collection/engines/{self.engine_id}/servingConfigs/default_serving_config"

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

        full_context = build_evaluation_prompt(application_text, rubric, instructions, schema)
        preamble = f"You are an expert SSC Accreditation Reviewer. Use the retrieved SSC guidelines from your Data Store to evaluate this application. Return ONLY valid JSON. APPLICATION DATA:\n\n{full_context}"
        
        query_text = f"Evaluate the applicant. Return ONLY a valid JSON object matching this schema: {json.dumps(schema)}"

        logger.info(f"Querying Discovery Engine (Query: {len(query_text)}, Preamble: {len(preamble)})")
        
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
