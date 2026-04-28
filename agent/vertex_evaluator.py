import json
import re
from typing import Dict, Any
import os
from google.cloud import discoveryengine_v1 as discoveryengine
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .evaluate import BaseEvaluator
from .config import logger

class VertexEvaluator(BaseEvaluator):
    def __init__(self, model_id: str = "stable", project_id: str = None, location: str = "us"):
        """
        Initializes the Discovery Engine Evaluator.
        Uses AnswerQuery API to target App Builder credits.
        Confirmed Location: 'us'
        Confirmed Engine ID: 'ssc-review-app_1776607831356'
        """
        self.project_id = project_id or os.getenv("PROJECT_ID", "project-9486ad0d-3ebc-4395-a7c")
        self.location = location
        self.engine_id = "ssc-review-app_1776607831356"
        self.model_version = model_id
        
        # Use regional endpoint as per Lessons Learned #4
        client_options = {"api_endpoint": f"{self.location}-discoveryengine.googleapis.com"}
        self.client = discoveryengine.ConversationalSearchServiceClient(client_options=client_options)
        
        logger.info(f"Initialized Discovery Engine Evaluator (Location: {self.location}, Engine: {self.engine_id})")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception)),
        before_sleep=lambda retry_state: logger.warning(f"Retrying evaluation (attempt {retry_state.attempt_number})...")
    )
    def evaluate(self, application_text: str, rubric: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """
        Grounded evaluation using AnswerQuery (Lessons Learned #3 and #5).
        """
        # Trim application text if it's excessively long
        if len(application_text) > 40000:
            logger.info(f"Trimming application text from {len(application_text)} to 40000 chars.")
            application_text = application_text[:40000]

        serving_config = f"projects/{self.project_id}/locations/{self.location}/collections/default_collection/engines/{self.engine_id}/servingConfigs/default_serving_config"

        schema = {
            "applicant_id": "string",
            "overall_summary": "string",
            "ai_recommendation": "Accept | Reject | Additional info needed",
            "ai_flags": [
                {"topic": "string", "reason": "string", "suggestion": "string"}
            ],
            "ready_for_human_review": True,
            "course_checklist": [
                {"module": "string", "course_code": "string", "is_satisfied": True}
            ],
            "criteria": [
                {
                    "criterion_id": "string", "criterion_name": "string",
                    "recommended_rating": "string", "confidence": 0.95,
                    "supporting_evidence": "string", "needs_human_attention": False
                }
            ]
        }

        # LESSONS LEARNED #3: Move data to preamble, keep query short.
        preamble = (
            "You are an expert SSC Accreditation Reviewer. Evaluate the applicant materials provided below against the guidelines in your Data Store.\n\n"
            "### EVALUATION LOGIC\n"
            "1. Suggest a recommendation: Accept, Reject, or Additional info needed.\n"
            "2. Flag assumptions or uncertainties in 'ai_flags'.\n"
            "3. Return ONLY a valid JSON object matching the requested schema.\n\n"
            f"### APPLICANT MATERIALS\n{application_text}\n\n"
            f"### RUBRIC\n{json.dumps(rubric)}\n\n"
            f"### OUTPUT SCHEMA\n{json.dumps(schema)}"
        )

        query_text = "Perform a grounded evaluation of the applicant materials using the SSC guidelines and course lists from the Data Store. Output the result in the specified JSON format."

        logger.info(f"Sending AnswerQuery request (Preamble: {len(preamble)} chars)")
        
        try:
            request = discoveryengine.AnswerQueryRequest(
                serving_config=serving_config,
                query=discoveryengine.Query(text=query_text),
                answer_generation_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec(
                    model_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.ModelSpec(
                        model_version=self.model_version
                    ),
                    prompt_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.PromptSpec(
                        preamble=preamble
                    ),
                    include_citations=True
                )
            )
            
            response = self.client.answer_query(request=request)
            answer_text = response.answer.answer_text
            
            # Clean up the response text to find JSON
            json_match = re.search(r'\{.*\}', answer_text, re.DOTALL)
            json_str = json_match.group(0) if json_match else answer_text

            result = json.loads(json_str)
            # Ensure the required arrays exist
            if "course_checklist" not in result: result["course_checklist"] = []
            if "criteria" not in result: result["criteria"] = []
            if "ai_flags" not in result: result["ai_flags"] = []
            
            return result

        except Exception as e:
            logger.error(f"❌ AnswerQuery Error: {e}")
            raise e
