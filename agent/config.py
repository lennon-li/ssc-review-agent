import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Base project path
BASE_DIR = Path(__file__).resolve().parent.parent

# Folder settings
APPLICATIONS_TEXT_DIR = BASE_DIR / "applications_text"
CRITERIA_DIR = BASE_DIR / "criteria"
INSTRUCTIONS_DIR = BASE_DIR / "instructions"

# Use /tmp for outputs and logs on Cloud Run
if os.getenv("K_SERVICE"):
    OUTPUTS_DIR = Path("/tmp/outputs")
    LOGS_DIR = Path("/tmp/logs")
else:
    OUTPUTS_DIR = BASE_DIR / "outputs"
    LOGS_DIR = BASE_DIR / "logs"

# Ensure dirs exist
for directory in [OUTPUTS_DIR, LOGS_DIR]:
    try:
        os.makedirs(directory, exist_ok=True)
    except Exception:
        pass

# Application Config
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure logging
handlers = [logging.StreamHandler()]

# Only add FileHandler if we have a writable logs directory (useful for local but risky on Cloud Run)
# Cloud Run preferred logging is stdout/stderr
if os.access(LOGS_DIR, os.W_OK):
    try:
        handlers.append(logging.FileHandler(LOGS_DIR / "app.log"))
    except Exception:
        pass

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger("ssc-review-agent")
