from typing import Dict, Any
import os
import json
from google.cloud import discoveryengine_v1 as discoveryengine
from .evaluate import BaseEvaluator
from .prompts import build_evaluation_prompt
from .config import logger

class VertexEvaluator(BaseEvaluator):
    def __init__(self, model_id: str = "gemini-2.0-flash-001", project_id: str = None, location: str = None):
        """
        Initializes the Vertex AI Search (Discovery Engine) Evaluator.
        Requires DATA_STORE_ID, PROJECT_ID, and LOCATION environment variables.
        """
        self.project_id = project_id or os.getenv("PROJECT_ID", "project-9486ad0d-3ebc-4395-a7c")
        self.location = location or os.getenv("LOCATION", "us-central1")
        self.data_store_id = os.getenv("DATA_STORE_ID")
        
        if not self.data_store_id:
            logger.error("DATA_STORE_ID not found in environment. VertexEvaluator will fail.")
        
        # Initialize the Discovery Engine client with regional endpoint
        client_options = (
            {"api_endpoint": f"{self.location}-discoveryengine.googleapis.com"}
            if self.location != "global"
            else None
        )
        self.client = discoveryengine.ConversationalSearchServiceClient(client_options=client_options)
        
        logger.info(f"Initialized VertexEvaluator (Discovery Engine) with project={self.project_id}, location={self.location}, data_store={self.data_store_id}")

    def evaluate(self, application_text: str, rubric: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """
        Evaluates an application using Vertex AI Search grounded generation.
        """
        print(f"--- [Discovery Engine] Starting grounded evaluation ---")
        
        if not self.data_store_id:
            raise ValueError("DATA_STORE_ID environment variable is required.")

        # Define the schema for structured output (same as before)
        schema = {
            "applicant_id": "string",
            "overall_summary": "string",
            "ready_for_human_review": "boolean",
            "course_checklist": [
                {
                    "module": "string",
                    "course_code": "string",
                    "title": "string",
                    "institution": "string",
                    "grade": "string",
                    "status": "string",
                    "is_satisfied": "boolean",
                    "note": "string"
                }
            ],
            "criteria": [
                {
                    "criterion_id": "string",
                    "criterion_name": "string",
                    "recommended_rating": "string",
                    "confidence": "number",
                    "supporting_evidence": "string",
                    "missing_evidence": "string",
                    "needs_human_attention": "boolean",
                    "reason_for_attention": "string",
                    "draft_comment": "string"
                }
            ]
        }

        # Build the prompt
        # Note: Discovery Engine Answer Query works best with a concise instruction.
        # We still use build_evaluation_prompt but might need to adjust if context length is an issue.
        full_prompt = build_evaluation_prompt(application_text, rubric, instructions, schema)
        
        # Construct the engine resource name
        serving_config = self.client.serving_config_path(
            project=self.project_id,
            location=self.location,
            data_store=self.data_store_id,
            serving_config="default_serving_config",
        )

        logger.info(f"Querying Discovery Engine Data Store: {self.data_store_id}")
        print("    Communicating with Discovery Engine API...")
        
        try:
            # Create the request for AnswerQuery
            request = discoveryengine.AnswerQueryRequest(
                serving_config=serving_config,
                query=discoveryengine.Query(text=full_prompt),
                session=None, # New session for each evaluation
                answer_generation_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec(
                    ignore_adversarial_query=True,
                    include_citations=True,
                    answer_language_code="en-US",
                    model_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.ModelSpec(
                        model_version="stable" # Using the stable version for reliability
                    ),
                    prompt_spec=discoveryengine.AnswerQueryRequest.AnswerGenerationSpec.PromptSpec(
                        preamble="You are an expert SSC Accreditation Reviewer. Base your answer ONLY on the provided search results from the data store. Return your response as a valid JSON object matching the requested schema strictly."
                    )
                )
            )
            
            response = self.client.answer_query(request)
            
            logger.info("Received response from Discovery Engine.")
            print("    Processing grounded answer...")
            
            # Extract the answer text (which should be JSON)
            answer_text = response.answer.answer_text
            
            # Clean up potential markdown formatting if the model wrapped it in ```json
            if "```json" in answer_text:
                answer_text = answer_text.split("```json")[1].split("```")[0].strip()
            elif "```" in answer_text:
                answer_text = answer_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(answer_text)
            
            # Simple validation
            if not result or "criteria" not in result:
                logger.error("Invalid or empty response from Discovery Engine.")
                raise ValueError("Discovery Engine returned an invalid evaluation format.")
                
            return result
            
        except Exception as e:
            logger.error(f"Discovery Engine evaluation failed: {e}")
            print(f"ERROR: Discovery Engine evaluation failed: {e}")
            raise
