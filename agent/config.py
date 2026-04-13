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
OUTPUTS_DIR = BASE_DIR / "outputs"
LOGS_DIR = BASE_DIR / "logs"

# Ensure dirs exist
for directory in [OUTPUTS_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Application Config
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("ssc-review-agent")
