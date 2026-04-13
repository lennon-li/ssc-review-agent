import json
import yaml
from pathlib import Path

def load_text(file_path: str) -> str:
    """Loads a plain text file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return path.read_text(encoding='utf-8')

def load_yaml(file_path: str) -> dict:
    """Loads a YAML file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_markdown(file_path: str) -> str:
    """Loads a markdown file as a string."""
    return load_text(file_path)

def load_json_schema(file_path: str) -> dict:
    """Loads a JSON schema."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
