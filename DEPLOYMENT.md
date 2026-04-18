# SSC Review Agent: Deployment & Infrastructure Documentation

This document records the setup and configuration of the SSC Accreditation Review Agent on Google Cloud.

## 1. Production Environment
- **Service URL:** [https://accreditation.biostats.ai](https://accreditation.biostats.ai)
- **Primary URL:** [https://ssc-review-agent-5ut3wa7lna-uc.a.run.app](https://ssc-review-agent-5ut3wa7lna-uc.a.run.app)
- **Platform:** Google Cloud Run (Fully Managed Serverless)
- **Region:** `us-central1`

## 2. Infrastructure Setup
### Containerization (Docker)
The application uses a hybrid image (`r-base:latest`) that installs both R and Python environments:
- **R Side:** Shiny, bslib, DT, reticulate, shinyjs.
- **Python Side:** `google-genai` (Gemini), `pypdf`, `python-docx`.
- **Port:** 8080 (Cloud Run default).

### Deployment Command
The app is deployed using the following gcloud command:
```bash
gcloud run deploy ssc-review-agent --source . --region us-central1 --allow-unauthenticated
```

## 3. Custom Domain Configuration (GoDaddy)
The subdomain `accreditation.biostats.ai` is mapped to the Cloud Run service via:
1.  **TXT Record:** Used for Google Search Console ownership verification.
2.  **CNAME Record:** `accreditation` pointing to `ghs.googlehosted.com`.
3.  **SSL:** Managed automatically by Google Cloud (Let's Encrypt).

## 4. Key Configurations & Fixes
- **Upload Limit:** Increased to **100MB** via `options(shiny.maxRequestSize)` in `app_cloud.R`.
- **Python Path:** Explicitly set to `/app` in the container to ensure R can see the `agent` module.
- **Table Styling:** Set to `bootstrap4` for compatibility with the container's version of the `DT` package.
- **Exports:** Added support for:
    - **DOCX:** Professional Word reports via `python-docx`.
    - **Markdown:** Text-based summary.
    - **LaTeX:** Source file for publication-quality reports.
    - **HTML:** Interactive preview.

## 5. Maintenance
To push updates to the live site, simply run the deploy command from this directory. Google Cloud Build will automatically handle the image recreation and zero-downtime rollover to the new version.
