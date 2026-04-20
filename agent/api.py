import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

def generate_html_report(result: Dict[str, Any]) -> str:
    """Generates a styled HTML report from the evaluation result."""
    html = f"""
    <div style="font-family: 'Open Sans', sans-serif; padding: 20px; color: #e0e0e0; background-color: #121212;">
        <h1 style="color: #E31837; border-bottom: 2px solid #E31837; padding-bottom: 10px;">Accreditation Review: {result.get('applicant_id', 'Unknown')}</h1>
        
        <h2 style="color: #E31837;">Executive Summary</h2>
        <div style="background: #1a1a1a; padding: 15px; border-left: 5px solid #005696; margin-bottom: 20px; color: #e0e0e0;">
            {result.get('overall_summary', 'No summary provided.')}
        </div>
        
        <h2 style="color: #E31837;">Course Checklist</h2>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; color: #e0e0e0;">
            <thead>
                <tr style="background: #1a1a1a; text-align: left;">
                    <th style="padding: 10px; border: 1px solid #333; color: #E31837;">Module</th>
                    <th style="padding: 10px; border: 1px solid #333; color: #E31837;">Course Code</th>
                    <th style="padding: 10px; border: 1px solid #333; color: #E31837;">Status</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for item in result.get('course_checklist', []):
        status = "✅ Satisfied" if item.get('is_satisfied') else "❌ Missing/Fail"
        html += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #333;">{item.get('module')}</td>
                    <td style="padding: 10px; border: 1px solid #333;">{item.get('course_code')}</td>
                    <td style="padding: 10px; border: 1px solid #333;">{status}</td>
                </tr>
        """
        
    html += """
            </tbody>
        </table>
        
        <h2 style="color: #E31837;">Detailed Criterion Assessment</h2>
    """
    
    for crit in result.get('criteria', []):
        status = "⚠️ Needs Attention" if crit.get('needs_human_attention') else "✅ Satisfied"
        color = "#dc3545" if crit.get('needs_human_attention') else "#28a745"
        html += f"""
        <div style="margin-bottom: 20px; border: 1px solid #333; border-radius: 4px; padding: 15px; background-color: #1a1a1a;">
            <div style="display: flex; justify-content: space-between; font-weight: bold; margin-bottom: 10px;">
                <span style="color: #E31837;">{crit.get('criterion_name')}</span>
                <span style="color: {color};">{status}</span>
            </div>
            <p style="font-size: 0.95em; color: #e0e0e0;">{crit.get('supporting_evidence', 'No evidence provided.')}</p>
        </div>
        """
        
    html += "</div>"
    return html

from .app_backend import run_folder_evaluation, find_applicant_photo, generate_markdown_report, generate_docx_report


app = FastAPI(title="SSC Accreditation Review API")

# Simple in-memory session store
sessions = {}

class EvaluationRequest(BaseModel):
    session_id: str
    evaluator_type: str = "vertex"

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    session_id = str(uuid.uuid4())
    temp_dir = Path(tempfile.gettempdir()) / "ssc_uploads" / session_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    file_names = []
    for file in files:
        file_path = temp_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_names.append(file.filename)
    
    sessions[session_id] = {
        "temp_dir": str(temp_dir),
        "files": file_names,
        "evaluation": None
    }
    
    return {"session_id": session_id, "files": file_names}

@app.post("/api/evaluate")
async def evaluate_application(request: EvaluationRequest):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[request.session_id]
    temp_dir = session_data["temp_dir"]
    
    try:
        # Run the evaluation using our rock-solid Discovery Engine backend
        result = run_folder_evaluation(temp_dir, request.evaluator_type)
        session_data["evaluation"] = result
        
        photo_name = find_applicant_photo(temp_dir)
        if photo_name:
            result["photo_url"] = f"/api/session/{request.session_id}/photo/{photo_name}"
            
        result["report_html"] = generate_html_report(result)
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/{session_id}/photo/{photo_name}")
async def get_photo(session_id: str, photo_name: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    photo_path = Path(sessions[session_id]["temp_dir"]) / photo_name
    if not photo_path.exists():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(photo_path)

@app.get("/api/session/{session_id}/export/{fmt}")
async def export_report(session_id: str, fmt: str):
    if session_id not in sessions or not sessions[session_id]["evaluation"]:
        raise HTTPException(status_code=404, detail="Result not found")
    
    result = sessions[session_id]["evaluation"]
    temp_dir = Path(sessions[session_id]["temp_dir"])
    
    if fmt == "markdown":
        md = generate_markdown_report(result)
        path = temp_dir / "report.md"
        with open(path, "w", encoding="utf-8") as f: f.write(md)
        return FileResponse(path, filename=f"SSC_Review_{result.get('applicant_id')}.md")
    elif fmt == "html":
        html = generate_html_report(result)
        path = temp_dir / "report.html"
        with open(path, "w", encoding="utf-8") as f: f.write(html)
        return FileResponse(path, filename=f"SSC_Review_{result.get('applicant_id')}.html")
    elif fmt == "docx":
        path = str(temp_dir / "report.docx")
        generate_docx_report(result, path)
        return FileResponse(path, filename=f"SSC_Review_{result.get('applicant_id')}.docx")
    raise HTTPException(status_code=400, detail="Format not supported")

@app.get("/health")
def health():
    return {"status": "ok"}

app.mount("/", StaticFiles(directory="public", html=True), name="static")
