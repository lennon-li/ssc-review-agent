from typing import Dict, Any, List

def render_system_instructions(instructions: str) -> str:
    return f"### Core Reviewer Instructions\n{instructions}"

def render_rubric(rubric: Dict[str, Any]) -> str:
    criteria_str = "\n".join([
        f"- {c['id']} ({c['name']}): {c['description']}" 
        for c in rubric.get('criteria', [])
    ])
    return f"### Evaluation Rubric\n{criteria_str}"

def render_application(application_text: str) -> str:
    return f"### Application Materials\n{application_text}"

def render_format_instructions(schema: Dict[str, Any]) -> str:
    import json
    return (
        "### Output Format\n"
        "You must return the evaluation in the following JSON format strictly:\n"
        f"{json.dumps(schema, indent=2)}\n"
        "Return ONLY the raw JSON string."
    )

def build_evaluation_prompt(
    application_text: str, 
    rubric: Dict[str, Any], 
    instructions: str, 
    schema: Dict[str, Any]
) -> str:
    parts = [
        render_system_instructions(instructions),
        render_rubric(rubric),
        render_application(application_text),
        render_format_instructions(schema)
    ]
    return "\n\n".join(parts)
