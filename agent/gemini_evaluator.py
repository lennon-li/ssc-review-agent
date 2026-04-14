from typing import Dict, Any
import os
import json
from google import genai
from .evaluate import BaseEvaluator
from .prompts import build_evaluation_prompt
from .config import logger

class GeminiEvaluator(BaseEvaluator):
    def __init__(self, model_id: str = "gemini-2.5-pro", api_key: str = None):
        self.model_id = model_id
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found in environment. GeminiEvaluator may fail.")
        self.client = genai.Client(api_key=self.api_key)

    def evaluate(self, application_text: str, rubric: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """
        Evaluates an application using the Gemini API.
        """
        # Load the schema for structured output validation
        # We can use the one from schemas/evaluation.schema.json if needed
        # For now, we rely on the prompt's format instructions.
        
        # In a more robust implementation, we would load the schema:
        # schema_path = os.path.join(os.path.dirname(__file__), "..", "schemas", "evaluation.schema.json")
        # with open(schema_path, "r") as f:
        #     schema = json.load(f)
        
        # Simple schema representation for the prompt
        schema = {
            "applicant_id": "string",
            "overall_summary": "string",
            "criteria": [
                {
                    "criterion_id": "string",
                    "criterion_name": "string",
                    "recommended_rating": "string",
                    "confidence": "number (0-1)",
                    "supporting_evidence": "string",
                    "missing_evidence": "string",
                    "draft_comment": "string"
                }
            ]
        }

        prompt = build_evaluation_prompt(application_text, rubric, instructions, schema)
        
        logger.info(f"Sending evaluation request to Gemini model: {self.model_id}")
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )
            
            result = json.loads(response.text)
            return result
        except Exception as e:
            logger.error(f"Gemini evaluation failed: {e}")
            raise
