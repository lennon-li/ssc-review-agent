import json
import re
from typing import Dict, Any
import os
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, GroundingConfig, DiscoveryEngine
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .evaluate import BaseEvaluator
from .config import logger

class VertexEvaluator(BaseEvaluator):
    def __init__(self, model_id: str = "gemini-1.5-pro", project_id: str = None, location: str = "us"):
        """
        Initializes the Vertex AI Grounded Generation Evaluator.
        Targets GenAI App Builder credits by using the DiscoveryEngine Tool.
        """
        self.project_id = project_id or os.getenv("PROJECT_ID", "project-9486ad0d-3ebc-4395-a7c")
        self.location = location
        self.model_id = model_id
        # Specific Data Store ID provided for credit consumption
        self.data_store_id = "ssc-rules-search_1776478612276_gcs_store"
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)
        
        # Configure the Grounding Tool
        # Format: projects/{project}/locations/{location}/collections/default_collection/dataStores/{datastore}
        self.datastore_path = f"projects/{self.project_id}/locations/{self.location}/collections/default_collection/dataStores/{self.data_store_id}"
        
        self.tool = Tool.from_retrieval(
            retrieval=vertexai.generative_models.retrieval.Retrieval(
                vertex_ai_search=vertexai.generative_models.retrieval.VertexAISearch(
                    datastore=self.datastore_path,
                )
            )
        )
        
        self.model = GenerativeModel(self.model_id)
        logger.info(f"Initialized Grounded GenerativeModel with Data Store: {self.data_store_id}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception)),
        before_sleep=lambda retry_state: logger.warning(f"Retrying evaluation (attempt {retry_state.attempt_number})...")
    )
    def evaluate(self, application_text: str, rubric: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """
        Grounded evaluation using the Vertex AI Search Tool (Bundled Billing).
        """
        # Trim application text if it's excessively long
        if len(application_text) > 40000:
            logger.info(f"Trimming application text from {len(application_text)} to 40000 chars for focus.")
            application_text = application_text[:40000]

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

        # Focus the prompt on logic and data. 
        # The AI will pull rules from the Data Store tool automatically.
        prompt = (
            "You are an expert SSC Accreditation Reviewer. Evaluate the following applicant materials against the provided rubric.\n\n"
            "CRITICAL: Use your 'Vertex AI Search' tool to retrieve and verify the official SSC Accreditation Guidelines and University Course Lists "
            "to ensure the applicant meets all requirements.\n\n"
            "### APPLICANT MATERIALS\n"
            f"{application_text}\n\n"
            "### EVALUATION RUBRIC\n"
            f"{json.dumps(rubric)}\n\n"
            "### OUTPUT FORMAT\n"
            f"Return ONLY a valid JSON object matching this schema: {json.dumps(schema)}"
        )

        logger.info(f"Sending Grounded Generation request (Prompt length: {len(prompt)})")
        
        try:
            response = self.model.generate_content(
                prompt,
                tools=[self.tool],
                generation_config={
                    "response_mime_type": "application/json",
                }
            )
            
            answer_text = response.text
            
            if not answer_text:
                logger.error("AI returned an empty response.")
                raise ValueError("Empty response from Vertex AI.")

            # Clean up the response text to find JSON
            json_match = re.search(r'\{.*\}', answer_text, re.DOTALL)
            json_str = json_match.group(0) if json_match else answer_text

            try:
                result = json.loads(json_str)
                # Ensure the required arrays exist
                if "course_checklist" not in result: result["course_checklist"] = []
                if "criteria" not in result: result["criteria"] = []
                
                # Log grounding metadata if available (for audit/verification)
                if hasattr(response, 'grounding_metadata'):
                    logger.info("Grounding metadata found. Citations used.")
                
                return result
            except Exception as parse_error:
                logger.error(f"JSON Parse Error. Raw text snippet: {answer_text[:200]}")
                raise ValueError("Malformed JSON returned from AI.")

        except Exception as e:
            logger.error(f"❌ Grounded Generation Error: {e}")
            raise e
