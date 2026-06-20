"""
Wasl AI API — FastAPI application.

Exposes all AI capabilities as REST endpoints:
- Resume parsing (PDF → structured JSON)
- Job matching (resume → ranked job recommendations)
- Skill gap analysis (candidate vs target role)
- Career path recommendations
- Learning plan generation
- Full pipeline (all-in-one analysis)
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import tempfile
from typing import Optional, List
from pydantic import BaseModel, Field

from wasl_ai.src.parser import parse_resume, extract_text_from_pdf
from wasl_ai.src.matcher import match_resume_to_jobs, match_resume_to_provided_jobs, get_all_jobs, get_available_domains
from wasl_ai.src.skill_analyzer import analyze_skill_gap
from wasl_ai.src.career_advisor import recommend_career_paths, recommend_from_parsed_resume
from wasl_ai.src.learning_planner import generate_learning_plan, generate_plan_from_gap_analysis


# ─── Request Models ───

class MatchRequest(BaseModel):
    resume_text: str = Field(..., description="Raw resume text or skill summary")
    resume_skills: Optional[List[str]] = Field(None, description="Explicit list of skills for better matching")
    top_k: int = Field(5, description="Number of top matches to return")
    domain_filter: Optional[str] = Field(None, description="Filter by job domain")
    experience_filter: Optional[str] = Field(None, description="Filter by experience level (intern/junior/mid/senior)")


class SkillAnalysisRequest(BaseModel):
    candidate_skills: List[str] = Field(..., description="List of candidate's skills")
    candidate_experience: Optional[List[str]] = Field(None, description="List of experience descriptions")
    candidate_education: Optional[List[str]] = Field(None, description="List of education entries")
    target_role: Optional[str] = Field(None, description="Target role title (e.g., 'ML Engineer')")
    target_job_id: Optional[int] = Field(None, description="ID of a specific job from our database to analyze against")


class CareerRequest(BaseModel):
    skills: List[str] = Field(..., description="List of candidate's skills")
    education: Optional[List[str]] = Field(None)
    experience: Optional[List[str]] = Field(None)
    projects: Optional[List[str]] = Field(None, description="List of project descriptions")
    interests: Optional[str] = Field(None, description="Career interests or goals")
    num_paths: int = Field(5, description="Number of career paths to recommend")


class LearningPlanRequest(BaseModel):
    target_role: str = Field(..., description="Target career role")
    current_skills: List[str] = Field(..., description="Skills the candidate already has")
    missing_skills: List[str] = Field(..., description="Skills the candidate needs to learn")
    education: Optional[List[str]] = Field(None)
    experience: Optional[List[str]] = Field(None)
    weekly_hours: int = Field(15, description="Available study hours per week")


class FirebaseJob(BaseModel):
    """Job schema matching what Flutter sends from Firebase."""
    id: str = Field(..., description="Firebase document ID")
    title: str = Field(..., description="Job title")
    description: str = Field('', description="Job description")
    skills: List[str] = Field(default_factory=list, description="Required skills (already flattened from reqSkills)")
    company: Optional[str] = Field(None)
    location: Optional[str] = Field(None)
    type: Optional[str] = Field(None, description="fulltime, parttime, etc.")
    salary: Optional[float] = Field(None)


class DynamicMatchRequest(BaseModel):
    """Request model for matching against Firebase jobs."""
    resume_text: str = Field(..., description="Raw resume text or skill summary")
    resume_skills: Optional[List[str]] = Field(None, description="Explicit list of skills for better matching")
    jobs: List[FirebaseJob] = Field(..., description="List of active jobs from Firebase")
    top_k: int = Field(5, description="Number of top matches to return")


# ─── App Setup ───

app = FastAPI(
    title="Wasl AI API",
    description="AI-driven career guidance and recruitment platform for the MENA market",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helper ───

def _save_upload_to_temp(file: UploadFile) -> str:
    """Save an uploaded file to a temp path and return the path."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        return tmp.name


def _extract_and_parse(tmp_path: str):
    """Extract text from a PDF and parse it with the LLM."""
    text = extract_text_from_pdf(tmp_path)
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
    parsed = parse_resume(text)
    return text, parsed


# ═══════════════════════════════════════════
#  1. RESUME PARSING
# ═══════════════════════════════════════════

@app.post("/resume/parse", tags=["Resume"])
async def parse_resume_endpoint(file: UploadFile = File(...)):
    """Upload a PDF resume and get parsed JSON data (name, email, skills, education, experience)."""
    tmp_path = _save_upload_to_temp(file)
    try:
        _, parsed = _extract_and_parse(tmp_path)
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ═══════════════════════════════════════════
#  2. JOB MATCHING
# ═══════════════════════════════════════════

@app.post("/jobs/match", tags=["Jobs"])
async def match_jobs_endpoint(request: MatchRequest):
    """Match a resume text against the job database using semantic + skill-based scoring."""
    try:
        matches = match_resume_to_jobs(
            resume_text=request.resume_text,
            resume_skills=request.resume_skills,
            top_k=request.top_k,
            domain_filter=request.domain_filter,
            experience_filter=request.experience_filter,
        )
        return {"matches": matches, "total_returned": len(matches)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/list", tags=["Jobs"])
async def list_jobs_endpoint(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    experience_level: Optional[str] = Query(None, description="Filter by experience level"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all available jobs with optional filtering and pagination."""
    try:
        result = get_all_jobs(
            domain=domain,
            experience_level=experience_level,
            page=page,
            page_size=page_size,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/domains", tags=["Jobs"])
async def list_domains_endpoint():
    """List all available job domains."""
    try:
        domains = get_available_domains()
        return {"domains": domains}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/match-dynamic", tags=["Jobs"])
async def match_dynamic_jobs_endpoint(
    file: UploadFile = File(...),
    jobs_json: str = Form(..., description="JSON string of Firebase jobs array"),
    top_k: int = Form(5, description="Number of top matches to return")
):
    """
    Match a resume PDF against jobs provided by the client (from Firebase).

    1. Parses the PDF to extract skills and experience.
    2. Uses sentence-transformer + skill-overlap logic to rank jobs.
    Job embeddings are cached by ID — first call computes, subsequent calls are instant.
    """
    import json as json_lib
    tmp_path = _save_upload_to_temp(file)
    try:
        raw_text, parsed_data = _extract_and_parse(tmp_path)
        skills = parsed_data.get('skills', [])
        experience = parsed_data.get('experience', [])
        
        match_text = f"Skills: {', '.join(skills)}. Experience: {experience}"
        dynamic_jobs = json_lib.loads(jobs_json)
        
        matches = match_resume_to_provided_jobs(
            resume_text=match_text,
            jobs=dynamic_jobs,
            resume_skills=skills,
            top_k=top_k,
        )
        return {
            "parsed_resume": parsed_data,
            "matches": matches, 
            "total_returned": len(matches)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ═══════════════════════════════════════════
#  3. SKILL GAP ANALYSIS
# ═══════════════════════════════════════════

@app.post("/skills/analyze", tags=["Skills"])
async def analyze_skills_endpoint(request: SkillAnalysisRequest):
    """
    Analyze the skill gap between a candidate and a target role or specific job.
    
    Provide either `target_role` (general analysis) or `target_job_id` (analyze against a specific job posting).
    """
    try:
        target_job_skills = None
        target_job_description = None
        target_role = request.target_role
        
        # If analyzing against a specific job from our database
        if request.target_job_id:
            jobs_result = get_all_jobs(page=1, page_size=1000)
            job = next((j for j in jobs_result['jobs'] if j['id'] == request.target_job_id), None)
            if not job:
                raise HTTPException(status_code=404, detail=f"Job with ID {request.target_job_id} not found.")
            target_role = job.get('title', target_role)
            target_job_skills = job.get('skills', [])
            target_job_description = job.get('description', '')
        
        if not target_role and not target_job_skills:
            raise HTTPException(status_code=400, detail="Provide either target_role or target_job_id.")
        
        result = analyze_skill_gap(
            candidate_skills=request.candidate_skills,
            candidate_experience=request.candidate_experience,
            candidate_education=request.candidate_education,
            target_role=target_role,
            target_job_skills=target_job_skills,
            target_job_description=target_job_description,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════
#  4. CAREER PATH RECOMMENDATIONS
# ═══════════════════════════════════════════

@app.post("/career/recommend", tags=["Career"])
async def career_recommend_endpoint(request: CareerRequest):
    """Get AI-powered career path recommendations based on skills, education, experience, and projects."""
    try:
        result = recommend_career_paths(
            skills=request.skills,
            education=request.education,
            experience=request.experience,
            projects=request.projects,
            interests=request.interests,
            num_paths=request.num_paths,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════
#  5. LEARNING PLAN
# ═══════════════════════════════════════════

@app.post("/learning/plan", tags=["Learning"])
async def learning_plan_endpoint(request: LearningPlanRequest):
    """Generate a structured, week-by-week learning plan to close skill gaps."""
    try:
        result = generate_learning_plan(
            target_role=request.target_role,
            current_skills=request.current_skills,
            missing_skills=request.missing_skills,
            candidate_education=request.education,
            candidate_experience=request.experience,
            weekly_hours=request.weekly_hours,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════
#  6. FULL PIPELINE (Parse → Match → Analyze → Recommend → Plan)
# ═══════════════════════════════════════════

@app.post("/resume/full-analysis", tags=["Full Pipeline"])
async def full_analysis_endpoint(
    file: UploadFile = File(...),
    target_role: Optional[str] = Query(None, description="Optional target role for skill gap analysis"),
    weekly_hours: int = Query(15, description="Available study hours per week for learning plan"),
    jobs_json: Optional[str] = Query(None, description="Optional JSON string of Firebase jobs array. If provided, matches against these instead of local DB."),
):
    """
    Complete AI analysis pipeline in one call:
    1. Parse the resume PDF
    2. Find matching jobs (from Firebase if jobs_json provided, otherwise local DB)
    3. Analyze skill gaps (against top match or target_role)
    4. Recommend career paths
    5. Generate a learning plan
    """
    import json as json_lib

    tmp_path = _save_upload_to_temp(file)
    try:
        # Step 1: Parse
        raw_text, parsed_data = _extract_and_parse(tmp_path)
        
        skills = parsed_data.get('skills', [])
        education = parsed_data.get('education', [])
        experience = parsed_data.get('experience', [])
        
        # Step 2: Match jobs
        match_text = f"Skills: {', '.join(skills)}. Experience: {experience}"
        
        if jobs_json:
            # Use dynamic Firebase jobs
            dynamic_jobs = json_lib.loads(jobs_json)
            job_matches = match_resume_to_provided_jobs(
                resume_text=match_text,
                jobs=dynamic_jobs,
                resume_skills=skills,
                top_k=5,
            )
        else:
            # Fallback to local jobs.json
            job_matches = match_resume_to_jobs(
                resume_text=match_text,
                resume_skills=skills,
                top_k=5,
            )
        
        # Step 3: Skill gap analysis
        gap_target = target_role
        gap_job_skills = None
        gap_job_desc = None
        
        if not gap_target and job_matches:
            # Use the top matching job as the target
            top_job = job_matches[0]['job']
            gap_target = top_job['title']
            gap_job_skills = top_job.get('skills', [])
            gap_job_desc = top_job.get('description', '')
        elif not gap_target:
            gap_target = "Software Engineer"  # fallback
        
        skill_gap = analyze_skill_gap(
            candidate_skills=skills,
            candidate_experience=experience,
            candidate_education=education,
            target_role=gap_target,
            target_job_skills=gap_job_skills,
            target_job_description=gap_job_desc,
        )
        
        # Step 4: Career path recommendations
        career_paths = recommend_career_paths(
            skills=skills,
            education=education,
            experience=experience,
        )
        
        # Step 5: Learning plan (based on skill gap)
        learning_plan = generate_plan_from_gap_analysis(
            gap_result=skill_gap,
            candidate_education=education,
            candidate_experience=experience,
            weekly_hours=weekly_hours,
        )
        
        return {
            "resume": parsed_data,
            "recommended_jobs": job_matches,
            "skill_gap_analysis": skill_gap,
            "career_recommendations": career_paths,
            "learning_plan": learning_plan,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ═══════════════════════════════════════════
#  HEALTH CHECK
# ═══════════════════════════════════════════

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}
