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

def extract_all_from_folder(folder_path: str) -> str:
    """
    Extracts text from all supported files in a folder and concatenates them.
    Supports PDF, DOCX, and plain text.
    """
    path = Path(folder_path)
    if not path.exists() or not path.is_dir():
        return ""
        
    combined_text = []
    for file_path in sorted(path.iterdir()):
        if not file_path.is_file():
            continue
            
        combined_text.append(f"\n--- Document: {file_path.name} ---\n")
        ext = file_path.suffix.lower()
        
        try:
            if ext == ".pdf":
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                for page in reader.pages:
                    combined_text.append(page.extract_text() or "")
            elif ext == ".docx":
                import docx
                doc = docx.Document(file_path)
                combined_text.append("\n".join([p.text for p in doc.paragraphs]))
            elif ext in [".txt", ".md"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    combined_text.append(f.read())
        except Exception as e:
            combined_text.append(f"[Error extracting {file_path.name}: {e}]")
            
    return "\n".join(combined_text)
