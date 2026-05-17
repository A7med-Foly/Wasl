"""
Skill Gap Analysis Engine for Wasl.

Compares a candidate's skills against a target job or role requirements.
Uses LLM to infer implicit skills and provide actionable gap analysis.
"""
import os
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

load_dotenv()


# --- Output Schema ---

class SkillGapResult(BaseModel):
    target_role: str = Field(description="The target role being analyzed against")
    readiness_score: int = Field(description="Overall readiness percentage 0-100")
    matched_skills: List[str] = Field(description="Skills the candidate already has that match the role")
    missing_critical: List[str] = Field(description="Critical/required skills the candidate lacks")
    missing_nice_to_have: List[str] = Field(description="Nice-to-have skills the candidate lacks")
    bonus_skills: List[str] = Field(description="Extra skills the candidate has beyond role requirements")
    inferred_skills: List[str] = Field(description="Skills implied by the candidate's existing skills (e.g., TensorFlow implies Python)")
    summary: str = Field(description="2-3 sentence summary of the candidate's readiness and key gaps")


# --- LLM Setup ---

def _get_llm():
    """Initialize the LLM via OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in environment")
    
    return ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )


# --- Core Analysis ---

def analyze_skill_gap(
    candidate_skills: List[str],
    candidate_experience: Optional[List[str]] = None,
    candidate_education: Optional[List[str]] = None,
    target_role: Optional[str] = None,
    target_job_skills: Optional[List[str]] = None,
    target_job_description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze the gap between a candidate's skills and a target role/job.
    
    You can either specify:
      - target_role: a general role title (e.g., "Machine Learning Engineer")
      - OR target_job_skills + target_job_description: a specific job posting
    
    The LLM will infer implicit skills and provide a structured gap analysis.
    
    Args:
        candidate_skills: List of the candidate's explicit skills.
        candidate_experience: Optional list of experience descriptions.
        candidate_education: Optional list of education entries.
        target_role: Target role title for general analysis.
        target_job_skills: Required skills from a specific job posting.
        target_job_description: Description of the target job.
    
    Returns:
        Dict matching SkillGapResult schema.
    """
    if not target_role and not target_job_skills:
        raise ValueError("Either target_role or target_job_skills must be provided")
    
    llm = _get_llm()
    parser = JsonOutputParser(pydantic_object=SkillGapResult)
    
    # Build the target context
    if target_job_skills and target_job_description:
        target_context = f"""
Target Job: {target_role or 'Specific Job Posting'}
Required Skills: {', '.join(target_job_skills)}
Job Description: {target_job_description[:1000]}
"""
    else:
        target_context = f"""
Target Role: {target_role}
(Use your knowledge of what skills are typically required for this role in the Egyptian/MENA tech market)
"""
    
    # Build candidate context
    experience_str = '\n'.join(candidate_experience) if candidate_experience else 'Not provided'
    education_str = '\n'.join(candidate_education) if candidate_education else 'Not provided'
    
    prompt = PromptTemplate(
        template="""You are an expert Career Skills Analyst specializing in the tech industry, particularly in the Egyptian and MENA job market.

Analyze the gap between this candidate's profile and the target role/job.

CANDIDATE PROFILE:
- Skills: {candidate_skills}
- Experience: {experience}
- Education: {education}

TARGET:
{target_context}

INSTRUCTIONS:
1. Identify which candidate skills match the target requirements (matched_skills).
2. Identify critical skills the candidate is missing that are essential for the role (missing_critical).
3. Identify nice-to-have skills the candidate lacks (missing_nice_to_have).
4. Identify any extra/bonus skills the candidate has beyond what's needed (bonus_skills).
5. Infer implicit skills from the candidate's existing skills. For example:
   - "TensorFlow" implies "Python", "Deep Learning", "NumPy"
   - "React" implies "JavaScript", "HTML", "CSS"
   - "Django" implies "Python", "SQL"
6. Calculate a readiness_score (0-100) considering:
   - How many critical skills are matched vs missing
   - The candidate's experience level relative to the role
   - Inferred skills that bridge gaps
7. Write a brief summary.

{format_instructions}
""",
        input_variables=["candidate_skills", "experience", "education", "target_context"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "candidate_skills": ', '.join(candidate_skills) if candidate_skills else 'None listed',
            "experience": experience_str,
            "education": education_str,
            "target_context": target_context,
        })
        return result
    except Exception as e:
        print(f"Error in skill gap analysis: {e}")
        return {
            "target_role": target_role or "Unknown",
            "readiness_score": 0,
            "matched_skills": [],
            "missing_critical": [],
            "missing_nice_to_have": [],
            "bonus_skills": [],
            "inferred_skills": [],
            "summary": f"Analysis failed: {str(e)}",
            "error": str(e),
        }


def analyze_against_job(
    candidate_skills: List[str],
    candidate_experience: Optional[List[str]],
    candidate_education: Optional[List[str]],
    job: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convenience function: analyze a candidate against a specific job from our database.
    """
    return analyze_skill_gap(
        candidate_skills=candidate_skills,
        candidate_experience=candidate_experience,
        candidate_education=candidate_education,
        target_role=job.get('title'),
        target_job_skills=job.get('skills', []),
        target_job_description=job.get('description', ''),
    )
