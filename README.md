# SSC Review Agent

## Purpose
The SSC Review Agent is a local-first application designed to automate the initial review of application materials. It evaluates applicants against specific criteria and instructions, producing structured assessments to assist human reviewers.

## Folder Structure
- `applications_raw/`: Original application files (ignored by git).
- `applications_text/`: Plain text versions of applications for processing.
- `criteria/`: YAML files defining evaluation rubrics.
- `instructions/`: Markdown files containing reviewer guidance.
- `schemas/`: JSON schemas for structured output validation.
- `outputs/`: Generated evaluation reports (ignored by git).
- `logs/`: Application logs and audit trails.
- `agent/`: Python backend logic (modular and evaluator-agnostic).
- `tests/`: Automated tests for the agent.
- `shiny_app/`: R Shiny frontend for human review.

## Local Workflow
1. Place the application text in `applications_text/`.
2. Define your rubric in `criteria/rubric.yml`.
3. Create a `.env` file from `.env.example`.
4. Run the evaluation agent:
   ```bash
   python -m agent.main --input applications_text/sample_01.txt --rubric criteria/rubric.yml --instructions instructions/reviewer_instructions.md --output outputs/sample_01_evaluation.json
   ```
5. Review the generated JSON in `outputs/` or the logs in `logs/app.log`.

## Development Roadmap
- [x] **Local Mock Evaluator**: Core architecture and CLI established.
- [ ] **Local Shiny App**: Enhance R Shiny frontend for interactive reviews.
- [ ] **Vertex AI Integration**: Implement `VertexEvaluator` to call real Gemini models.
- [ ] **Containerization**: Create Dockerfiles for Python and R Shiny environments.
- [ ] **Cloud Run Deployment**: Deploy the modular backend to Google Cloud.
- [ ] **GCS/BigQuery Integration**: Scalable data storage for large batches of applications.

## Key Design Choices
- **Evaluator Interface**: A base `Evaluator` class allows seamless switching between mock, local (e.g., Ollama), and cloud (e.g., Vertex AI) models.
- **Prompt Isolation**: Prompts are constructed from modular components in `prompts.py`.
- **Structured Logging**: All operations are logged to `logs/app.log` for debugging and auditing.
