from typing import Dict, Any
import os
import json
from google.cloud import discoveryengine_v1 as discoveryengine

from .evaluate import BaseEvaluator
from .prompts import build_evaluation_prompt
from .config import logger

class VertexEvaluator(BaseEvaluator):
    def __init__(self, model_id: str = None, project_id: str = None, location: str = None):
        """
        Initializes the Discovery Engine Evaluator.
        Targets the correct multi-region 'us' endpoint and your newly created Enterprise Engine (App).
        """
        self.project_id = project_id or os.getenv("PROJECT_ID", "project-9486ad0d-3ebc-4395-a7c")
        self.location = "us" 
        
        # Using the exact Engine ID you just created and linked to the Enterprise App
        self.engine_id = "ssc-review-app_1776607831356"
        
        endpoint = f"{self.location}-discoveryengine.googleapis.com"
        client_options = {"api_endpoint": endpoint}
        
        self.client = discoveryengine.ConversationalSearchServiceClient(client_options=client_options)
        logger.info(f"Initialized Discovery Engine Evaluator at {endpoint} for project={self.project_id}, location={self.location}")

    def evaluate(self, application_text: str, rubric: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """
        Grounded evaluation using Discovery Engine AnswerQuery.
        This uses your App Builder credits (AI Application SKU) because the Engine is Enterprise tier.
        """
        serving_config = f"projects/{self.project_id}/locations/{self.location}/collections/default_collection/engines/{self.engine_id}/servingConfigs/default_serving_config"

        # The exact schema required by the Shiny frontend
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

        # Build the full context using your existing prompt builder
        full_context = build_evaluation_prompt(application_text, rubric, instructions, schema)
        
        # We put the massive application text and rubric inside the preamble (no strict length limit)
        preamble = f"You are an expert SSC Accreditation Reviewer. Use the retrieved SSC guidelines from your Data Store to evaluate this application. Here is the application data and instructions:\n\n{full_context}"
        
        # The query is strictly under 2000 chars and enforces the exact JSON schema
        query_text = f"Evaluate the applicant based on the preamble. You MUST return ONLY a valid JSON object strictly matching this schema, filling out the arrays completely based on the applicant's data: {json.dumps(schema)}. Ensure all arrays are properly formatted with square brackets even if empty."

        logger.info(f"Querying Discovery Engine AnswerQuery on Engine {self.engine_id} (Query length: {len(query_text)}, Preamble length: {len(preamble)})")
        
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
            
            # Robust JSON parsing
            try:
                if "```json" in answer_text:
                    answer_text = answer_text.split("```json")[1].split("```")[0].strip()
                elif "```" in answer_text:
                    answer_text = answer_text.split("```")[1].split("```")[0].strip()
                    
                result = json.loads(answer_text)
                
                # Ensure the required arrays exist
                if "course_checklist" not in result:
                    result["course_checklist"] = []
                if "criteria" not in result:
                    result["criteria"] = []
                    
                return result
                
            except Exception as parse_error:
                logger.error(f"Failed to parse JSON from Discovery Engine. Raw text: {answer_text}")
                raise ValueError("The AI model failed to format its response correctly (or returned an empty summary). Please click Run again.")

        except Exception as e:
            logger.error(f"❌ Discovery Engine evaluation failed: {e}")
            raise e
