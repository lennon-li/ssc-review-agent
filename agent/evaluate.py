from abc import ABC, abstractmethod
from typing import Dict, Any
from .prompts import build_evaluation_prompt

class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self, application_text: str, rubric: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """Base interface for evaluation."""
        pass

class MockEvaluator(BaseEvaluator):
    def evaluate(self, application_text: str, rubric: Dict[str, Any], instructions: str) -> Dict[str, Any]:
        """
        A mock evaluator that returns a deterministic evaluation structure.
        """
        # In a real scenario, this is where you might call an LLM using the prompt from prompts.py
        # prompt = build_evaluation_prompt(application_text, rubric, instructions, schema)
        
        criteria_list = rubric.get("criteria", [])
        evaluations = []

        for criterion in criteria_list:
            evaluations.append({
                "criterion_id": criterion["id"],
                "criterion_name": criterion["name"],
                "recommended_rating": "Strongly Met",
                "confidence": 0.85,
                "supporting_evidence": f"Mock evidence found in text for {criterion['name']}.",
                "missing_evidence": "None noted in mock mode.",
                "draft_comment": f"The candidate shows high proficiency in {criterion['name']}.",
                "reviewer_override": ""
            })

        return {
            "applicant_id": "applicant_001",
            "overall_summary": "Overall, the mock candidate is a strong fit for the position.",
            "criteria": evaluations
        }

# Function to get the configured evaluator
def get_evaluator(evaluator_type: str = "mock") -> BaseEvaluator:
    if evaluator_type == "mock":
        return MockEvaluator()
    # Add other evaluators (e.g., VertexEvaluator) here later
    raise ValueError(f"Unknown evaluator type: {evaluator_type}")

# Legacy support for main.py (can be removed once main.py is updated)
def mock_evaluate(application_text: str, rubric: Dict[str, Any], instructions: str) -> Dict[str, Any]:
    return MockEvaluator().evaluate(application_text, rubric, instructions)
