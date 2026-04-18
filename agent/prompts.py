from typing import Dict, Any, List
import json

def render_system_instructions(instructions: str) -> str:
    return (
        "### Core Reviewer Instructions\n"
        f"{instructions}\n\n"
        "### Operational Requirements for Reliability\n"
        "1. **Professional Identity Mandate**: This accreditation is strictly for Professional Statisticians. You must distinguish between a statistician and a data scientist or a person from another field using models. If the application is clearly from another field (e.g. Computer Science, Machine Learning, Data Science) without a rigorous statistical education foundation, flag this as a major concern.\n"
        "2. **Education Primacy**: Education is the most important component. A statistician is defined by their knowledge of study design, sampling, and classical inference. If education is missing or insufficient based on the checklist, do not recommend approval.\n"
        "3. **Evidence-Only Reasoning**: Every rating must be supported by direct evidence from the application materials. If no evidence exists, state it clearly.\n"
        "4. **Missing Evidence**: Explicitly list what information is required by the rubric but missing from the application.\n"
        "5. **Uncertainty & Conflict**: If the evidence is contradictory or you are unsure how to interpret it against the rubric, set 'needs_human_attention' to true and explain why in the 'draft_comment'.\n"
        "6. **Strict JSON**: You must return a valid JSON object matching the requested schema. Do not include any text outside the JSON block."
    )

def render_rubric(rubric: Dict[str, Any]) -> str:
    criteria_str = "\n".join([
        f"- {c['id']} ({c['name']}): {c['description']}" 
        for c in rubric.get('criteria', [])
    ])
    return f"### Evaluation Rubric\n{criteria_str}"

def render_application(application_text: str) -> str:
    return f"### Application Materials\n{application_text}"

def render_format_instructions(schema: Dict[str, Any]) -> str:
    return (
        "### Output Format\n"
        "You must return the evaluation in the following JSON format strictly:\n"
        f"{json.dumps(schema, indent=2)}\n"
        "Ensure all boolean fields are correctly set based on the evidence found."
    )

def build_evaluation_prompt(
    application_text: str, 
    rubric: Dict[str, Any], 
    instructions: str, 
    schema: Dict[str, Any]
) -> str:
    parts = [
        "## Role\nYou are an expert SSC Accreditation Reviewer. Your goal is to provide a reliable, evidence-based assessment.",
        render_system_instructions(instructions),
        render_rubric(rubric),
        render_application(application_text),
        render_format_instructions(schema)
    ]
    return "\n\n".join(parts)
