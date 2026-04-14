# Project: SSC Accreditation Review Agent
A local-first application review agent for SSC-style accreditation review workflows.

## Current Goal
Build the local end-to-end prototype first.

## System Requirements
- Read application materials
- Read review instructions and criteria
- Produce structured criterion-by-criterion assessments
- Draft a filled evaluation form for human review
- Support later addition of a Shiny front end
- Support later deployment to Google Cloud with a backend agent

## Current Stage
- Local project structure exists
- Organizing instructions, templates, guidelines, and examples
- **NEW:** PDF text extraction support via `extract_pdf.py` (using `pypdf`)
- **NEW:** Gemini API integration via `GeminiEvaluator` (using `google-genai`)
- **CRITICAL:** Do not add cloud deployment code yet
- **CRITICAL:** Do not add Google Drive integration yet
- **CRITICAL:** Do not add a database yet

## Design Principles
- Modular backend
- Structured outputs, not free-form only
- Human review remains in control
- Evidence must be tied to each criterion
- Keep code simple and auditable

## Folder Roles
- `instructions/`: Active reviewer guidance
- `criteria/`: Rubric and scoring logic
- `templates/`: Fillable output templates
- `schemas/`: Machine-readable output structure
- `guidelines/`: Source policy/guidance documents
- `reference/`: Static supporting reference
- `examples/`: Past examples or sample cases
- `applications_raw/`: Original files
- `applications_text/`: Extracted text
- `outputs/`: Generated evaluations and forms

## Working Guidelines
- Inspect existing files first
- Do not overwrite good work unnecessarily
- Explain key design choices
- Show exact files changed
