from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import tempfile
from wasl_ai.src.parser import parse_resume, extract_text_from_pdf
from wasl_ai.src.matcher import match_resume_to_jobs
from pydantic import BaseModel

class MatchRequest(BaseModel):
    resume_text: str


# Enable CORS for Flutter/Web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/resume/parse")
async def parse_resume_endpoint(file: UploadFile = File(...)):
    """
    Upload a PDF resume and get parsed JSON data.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Create a temporary file to save the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Extract Text
        text = extract_text_from_pdf(tmp_path)
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
        
        # Parse with LLM
        data = parse_resume(text)
        return data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.post("/jobs/match")
async def match_jobs_endpoint(request: MatchRequest):
    """
    Match a raw resume text to available jobs.
    """
    try:
        matches = match_resume_to_jobs(request.resume_text)
        return {"matches": matches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resume/parse-and-match")
async def parse_and_match_endpoint(file: UploadFile = File(...)):
    """
    Upload a PDF, parse it, AND find matching jobs in one go.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # 1. Extract
        text = extract_text_from_pdf(tmp_path)
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract text.")
        
        # 2. Parse (LLM)
        parsed_data = parse_resume(text)
        
        # 3. Match (Vectors)
        # We construct a rich text representation from the parsed data for better matching
        # e.g., "Skills: Python, SQL. Experience: ML Engineer"
        match_text = f"Skills: {', '.join(parsed_data.get('skills', []))}. " \
                     f"Experience: {parsed_data.get('experience', [])}"
        
        matches = match_resume_to_jobs(match_text)
        
        return {
            "resume": parsed_data,
            "recommended_jobs": matches
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@app.get("/health")
def health_check():
    return {"status": "ok"}
