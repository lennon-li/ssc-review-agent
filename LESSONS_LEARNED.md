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

## 8. Grounded AI Stability (AnswerQuery)
**What happened:** 80% failure rate when processing large application files (140k+ characters) due to "summary could not be generated" errors.
**The Reality:** Trimming input to ~40k characters significantly improves the "Groundedness" success rate for the `AnswerQuery` API. 
**The Lesson:** 
1. **Context Trimming:** Prioritize the first 40k characters (where transcripts and CVs usually reside). 
2. **Silent Retries:** Using the `tenacity` library to automatically retry failed AI calls (up to 3 times) masks minor transient errors and provides a smoother user experience.
3. **Robust JSON Extraction:** LLMs occasionally add conversational "chatter" even when asked for pure JSON. Using Regex (`re.search(r'\{.*\}', text, re.DOTALL)`) is a mandatory guardrail for production parsing.
