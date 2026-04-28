# Lessons Learned: Building the SSC Review Agent

This document captures the valuable experiences, architectural decisions, and hard-learned troubleshooting lessons from building a production-grade RAG (Retrieval-Augmented Generation) application using Google Cloud Vertex AI Agent Builder.

## 1. The "It Worked Yesterday" Fallacy (Silent Failures)
**What happened:** The application appeared to be working perfectly one day, but completely failed the next when environment variables were cleared.
**The Reality:** The app was never actually using the Discovery Engine / App Builder credits. A malformed environment variable (`DATA_STORE_ID="ssc-rules... PROJECT_ID=..."`) caused the connection to fail silently. The backend code caught the error and secretly fell back to a standard, ungrounded Gemini model. 
**The Lesson:** Just because an AI app returns a good-looking output doesn't mean it's using the correct infrastructure. Always verify the logs to ensure the *exact* intended API endpoint (e.g., `AnswerQuery`) is successfully resolving.

## 2. RAG Architecture: "The Brain" vs. "The Knowledge"
**What happened:** There was confusion over whether to upload the custom `SKILL.md` (reviewer instructions) into the Google Cloud Data Store alongside the SSC rulebook PDFs.
**The Reality:** 
* **The Knowledge (Data Store):** This is for factual, static documents (Course lists, official SSC guidelines). The AI *searches* this.
* **The Brain (Code/Prompt):** This is for behavioral instructions, logic (e.g., A.Stat vs P.Stat rules), and output formatting. This MUST be passed in the `preamble` (System Prompt) of the API call. 
**The Lesson:** Never put behavioral instructions into a vector database/data store. The AI will treat them as search results rather than strict commands, leading to hallucinations and ignored rules.

## 3. Bypassing the 2,000 Character Hard Limit
**What happened:** The `discoveryengine.AnswerQuery` API crashed with a `400 Error: query length should be <= 2000 characters` when we passed the applicant's resume.
**The Reality:** The `query` parameter is strictly designed for short, search-engine-like questions ("What is A.Stat?"). It physically rejects large document payloads.
**The Hack / Lesson:** The `prompt_spec.preamble` parameter accepts over 100,000 characters. By moving the massive application payload (10,000+ words) and the JSON instructions into the `preamble`, and keeping the actual `query` to a single sentence ("Evaluate the applicant based on the preamble"), we successfully bypassed the API limit while still triggering the correct App Builder credits.

## 4. Google Cloud Regionality is Unforgiving
**What happened:** We repeatedly hit `501 Not Implemented` and `404 Not Found` errors when querying the Data Store.
**The Reality:** 
1. If your Data Store is in the `us` multi-region, you CANNOT query it from the `us-central1` or `global` endpoints. You must use `us-discoveryengine.googleapis.com`.
2. The project was actively blocking generative models in `us-central1`, returning 404s for standard Gemini calls. 
**The Lesson:** When an API says "404", it doesn't mean your code is wrong. It often means the specific Region/Location string in your client initialization doesn't perfectly match the physical location of the resource in Google Cloud.

## 5. Data Store vs. Enterprise Engine (The Billing Trap)
**What happened:** We tried to query the Data Store directly for grounded generation and failed. We also got a warning about incurring standard charges instead of using App Builder credits.
**The Reality:** A Data Store is just a storage box. To use LLMs and consume "AI Application" credits, you must create a **Search App (Engine)** that sits on top of the Data Store. 
**The Lesson:** You must toggle **"Enterprise Edition"** and **"Advanced LLM features"** to ON when creating the App in the Google Cloud Console. Your code must then query the *Engine ID*, not the Data Store ID.

## 7. Deployment & Infrastructure Stability
**What happened:** Encountered "Container import failed" on Cloud Run despite a successful build.
**The Reality:** This usually indicates an IAM permission gap where the Cloud Run service agent cannot pull the image from Artifact Registry.
**The Lesson:** Explicitly granting `roles/artifactregistry.reader` to both the Compute Service Account AND the Cloud Run Service Agent (`service-[PROJECT_NUMBER]@serverless-robot-prod.iam.gserviceaccount.com`) is often necessary for cross-repository or custom registry deployments.

## 9. Credit-Aware Orchestration (Maximizing AI App Builder Credits)
**What happened:** High costs were detected in the general credit pool despite using the Discovery Engine, while the $1,386 GenAI credit remained unused.
**The Reality:** The system was "prompt stuffing"—sending the entire rulebook in the prompt context. This forced the underlying LLM to do the work using its own internal knowledge/context window (billed to general credits) instead of performing a retrieval operation from the Data Store (billed to App Builder credits).
**The Lesson:** To maximize credits, use **Lean Prompting**. Keep the prompt focused on behavioral logic and the specific case data. Use a descriptive `query` that explicitly instructs the engine to "Search" the Data Store. This triggers the retrieval SKU and shifts the billing from the LLM to the App Builder credit pool.

## 10. Build Hygiene & Deployment Stability
**What happened:** Deployment failed with "Container import failed" due to massive image size (~27GB Artifact Registry repo) and missing runtime dependencies (`tenacity`).
**The Reality:** 
1. Without a `.dockerignore` file, the local `venv/` and multi-hundred-megabyte `.zip` archives were being baked into the container.
2. Artifact Registry repositories can become cluttered and slow over time; moving to a fresh, smaller repository (`ssc-repo`) resolved the import issues.
**The Lesson:** 
1. **Always use `.dockerignore`**: Exclude `venv`, `.git`, and large temporary files.
2. **Modular Repositories**: If a default deployment repository becomes unreliable or excessively large, switch to a dedicated, clean repository.
3. **Explicit Dependencies**: Always verify `requirements.txt` against your imports before deploying.
