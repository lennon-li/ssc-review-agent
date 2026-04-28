# SSC Review Agent: System Architecture & Billing Flow

This diagram illustrates the end-to-end flow of the SSC Review Agent. It highlights the boundary between standard Google Cloud infrastructure (billed normally) and the Vertex AI Agent Builder components (which consume your $1,386.25 AI Application credits).

```mermaid
sequenceDiagram
    autonumber

    box rgba(200, 225, 255, 0.2) "Google Cloud Run (Standard Compute Billing)"
    actor User as Human Reviewer
    participant Shiny as R Shiny UI
    participant Python as Python Backend (app_backend.py)
    participant Skill as Local SKILL.md (The Brain)
    end

    box rgba(230, 255, 230, 0.4) "Vertex AI Agent Builder ($1,386.25 Credit Pool)"
    participant Engine as Search App / Engine<br/>(Enterprise Edition)
    participant DataStore as Data Store<br/>(ssc-guidelines-docs)
    participant Gemini as Vertex AI Gemini LLM
    end

    box rgba(255, 240, 200, 0.3) "Google Cloud Storage (Standard Storage Billing)"
    participant GCS as Cloud Storage Bucket<br/>(Rulebooks & Course Lists)
    end

    %% Setup Phase
    note over GCS, DataStore: Background Setup (Once)
    GCS->>DataStore: 0. Import & Vectorize SSC Guidelines (PDFs/Docx)
    DataStore->>Engine: 0. Linked as Grounding Source

    %% Runtime Phase
    note over User, Gemini: Runtime Evaluation Flow (Credit Optimized)
    User->>Shiny: Uploads 12 Applicant Files (Transcripts, Resumes)
    Shiny->>Python: Sends raw files for processing
    Python->>Python: Extracts text (~10,000 words)
    
    Python->>Skill: Reads evaluation logic (NOT knowledge)
    Skill-->>Python: Returns lean behavioral instructions
    
    note over Python: Assembles "Lean Preamble" (Applicant Data + Logic + JSON Schema)
    
    Python->>Engine: AnswerQueryRequest (Lean Preamble + Search Query)
    note right of Python: REGIONAL ENDPOINT: us-discoveryengine.googleapis.com
    note right of Python: ENGINE ID: ssc-review-app_1776607831356
    
    Engine->>DataStore: Searches Knowledge Base (SSC Rules / Course Lists)
    DataStore-->>Engine: Returns matching text chunks from Guidelines
    
    Engine->>Gemini: Sends Applicant Data + Logic + RETRIEVED Rules
    Gemini-->>Engine: Generates strict JSON evaluation
    
    Engine-->>Python: Returns final JSON payload
    
    Python->>Shiny: Parses JSON and structures tables
    Shiny-->>User: Displays Dashboard (Summary, Checklist, Criteria)

```

## Understanding the Billing Boundaries

### 🟢 The "Green Zone" (App Builder Credits)
The entire right side of the diagram (The **Search App / Engine**, the **Data Store**, and the underlying **Gemini** model it uses) is wrapped into a single Google Cloud SKU called **AI Application - Grounded Generation**.
* **Credit Strategy:** By keeping the preamble "lean" (logic-only) and using a descriptive `query` (e.g., *"Search the SSC guidelines for..."*), we force the system to perform a retrieval operation. This retrieval step is what triggers the specialized $1,386.25 credit pool.
* **Avoidance:** If you include the full rulebooks in the prompt context, you pay standard **Vertex AI Gemini** rates (billed to general credits). 

### 🔵 The "Blue/Orange Zones" (Standard / Free Tier Billing)
* **Cloud Run (R Shiny + Python):** Hosting the web interface and running the text extraction scripts uses standard CPU/RAM. Cloud Run has a massive free tier (2 million requests/month), so this costs virtually nothing.
* **Cloud Storage:** Storing your PDF guidelines costs standard storage rates (pennies per month).
* **Build Hygiene:** A `.dockerignore` file ensures that local environments (`venv/`) and large temporary files are not uploaded, keeping build times fast and deployment images small.
