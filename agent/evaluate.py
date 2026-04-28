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
                "needs_human_attention": False,
                "draft_comment": f"The candidate shows high proficiency in {criterion['name']}.",
                "reviewer_override": ""
            })

        return {
            "applicant_id": "applicant_001",
            "overall_summary": "Overall, the mock candidate is a strong fit for the position.",
            "ai_recommendation": "Accept",
            "ai_flags": [
                {
                    "topic": "Professional Experience",
                    "reason": "Assumption",
                    "suggestion": "AI assumed the 2-year internship counts towards the 6-year requirement. Human should verify."
                }
            ],
            "ready_for_human_review": True,
            "criteria": evaluations
        }

# Function to get the configured evaluator
def get_evaluator(evaluator_type: str = "vertex") -> BaseEvaluator:
    if evaluator_type == "vertex":
        from .vertex_evaluator import VertexEvaluator
        return VertexEvaluator()
    elif evaluator_type == "gemini":
        from .gemini_evaluator import GeminiEvaluator
        return GeminiEvaluator()
    elif evaluator_type == "mock":
        return MockEvaluator()
    
    raise ValueError(f"Unknown evaluator type: {evaluator_type}")

# Legacy support for main.py (can be removed once main.py is updated)
def mock_evaluate(application_text: str, rubric: Dict[str, Any], instructions: str) -> Dict[str, Any]:
    return MockEvaluator().evaluate(application_text, rubric, instructions)
