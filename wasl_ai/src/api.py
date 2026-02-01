from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import tempfile
from wasl_ai.src.parser import parse_resume, extract_text_from_pdf

app = FastAPI(title="Wasl AI API", version="0.1.0")

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

@app.get("/health")
def health_check():
    return {"status": "ok"}
