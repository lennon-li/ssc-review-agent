from typing import Dict, Any

def export_to_docx(evaluation: Dict[str, Any], output_path: str):
    """
    Stub for exporting the evaluation to a DOCX format.
    Requires python-docx library.
    """
    print(f"Stub: Exporting evaluation to DOCX at {output_path}")
    pass

def export_to_pdf(evaluation: Dict[str, Any], output_path: str):
    """
    Stub for exporting the evaluation to a PDF format.
    Requires fpdf2 or reportlab library.
    """
    print(f"Stub: Exporting evaluation to PDF at {output_path}")
    pass
