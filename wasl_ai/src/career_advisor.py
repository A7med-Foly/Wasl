"""
Career Path Recommendation Engine for Wasl.

Uses LLM to analyze a candidate's full profile (skills, education, experience, projects)
and generate personalized career path recommendations with rationale and next steps.
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

class CareerPath(BaseModel):
    title: str = Field(description="Career path title (e.g., 'Machine Learning Engineer')")
    fit_score: int = Field(description="How well this path fits the candidate, 0-100")
    rationale: str = Field(description="2-3 sentences explaining why this path suits the candidate")
    current_strengths: List[str] = Field(description="Candidate's existing strengths relevant to this path")
    skills_to_develop: List[str] = Field(description="Key skills the candidate needs to develop for this path")
    next_steps: List[str] = Field(description="3-5 concrete actionable next steps")
    timeline: str = Field(description="Estimated timeline to become job-ready (e.g., '3-6 months')")
    market_demand: str = Field(description="Current demand level: 'High', 'Medium', or 'Low' in the MENA/Egyptian market")


class CareerRecommendation(BaseModel):
    candidate_summary: str = Field(description="Brief 2-3 sentence profile summary of the candidate")
    career_paths: List[CareerPath] = Field(description="3-5 recommended career paths, sorted by fit score descending")
    general_advice: str = Field(description="General career development advice for this candidate")


# --- LLM Setup ---

def _get_llm():
    """Initialize the LLM via OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in environment")
    
    return ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0.3,  # Slightly creative for career advice
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    )


# --- Core Recommendation ---

def recommend_career_paths(
    skills: List[str],
    education: Optional[List[str]] = None,
    experience: Optional[List[str]] = None,
    projects: Optional[List[str]] = None,
    interests: Optional[str] = None,
    num_paths: int = 5,
) -> Dict[str, Any]:
    """
    Generate personalized career path recommendations based on the candidate's profile.
    
    Args:
        skills: List of the candidate's skills.
        education: List of education entries.
        experience: List of work experience descriptions.
        projects: List of project descriptions (important for fresh graduates).
        interests: Optional text describing career interests/goals.
        num_paths: Number of career paths to recommend (default 5).
    
    Returns:
        Dict matching CareerRecommendation schema.
    """
    llm = _get_llm()
    parser = JsonOutputParser(pydantic_object=CareerRecommendation)
    
    # Build candidate profile
    skills_str = ', '.join(skills) if skills else 'Not provided'
    education_str = '\n  - '.join(education) if education else 'Not provided'
    experience_str = '\n  - '.join(experience) if experience else 'No work experience (likely fresh graduate)'
    projects_str = '\n  - '.join(projects) if projects else 'Not provided'
    interests_str = interests if interests else 'Not specified'
    
    prompt = PromptTemplate(
        template="""You are a senior Career Advisor AI specializing in the tech industry in Egypt and the MENA region. You have deep knowledge of the local job market, in-demand skills, and career trajectories.

Analyze this candidate's profile and recommend {num_paths} personalized career paths.

CANDIDATE PROFILE:
- Skills: {skills}
- Education:
  - {education}
- Work Experience:
  - {experience}
- Personal Projects:
  - {projects}
- Career Interests: {interests}

IMPORTANT GUIDELINES:
1. Consider the Egyptian/MENA tech job market specifically:
   - High demand areas: AI/ML, Cloud/DevOps, Mobile (Flutter), Full-Stack Web, Data Engineering
   - Growing areas: Cybersecurity, Product Management, UI/UX
   - Companies hiring: Valeo, Vodafone Egypt, Orange, e&, Careem, Instabug, startups
2. For fresh graduates, weight projects and skills heavily (more than lack of experience).
3. Be realistic about timelines — consider the candidate's current level.
4. Each career path should feel distinct (don't recommend 5 variations of the same role).
5. Include at least one "stretch" path that's ambitious but achievable.
6. Rank paths by fit_score (highest first).
7. Make next_steps extremely concrete and actionable (not vague like "learn more about AI").

{format_instructions}
""",
        input_variables=["skills", "education", "experience", "projects", "interests", "num_paths"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "skills": skills_str,
            "education": education_str,
            "experience": experience_str,
            "projects": projects_str,
            "interests": interests_str,
            "num_paths": str(num_paths),
        })
        return result
    except Exception as e:
        print(f"Error in career recommendation: {e}")
        return {
            "candidate_summary": "Analysis could not be completed.",
            "career_paths": [],
            "general_advice": f"Error: {str(e)}",
            "error": str(e),
        }


def recommend_from_parsed_resume(parsed_resume: Dict[str, Any], interests: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function: generate career paths directly from a parsed resume output.
    
    Args:
        parsed_resume: Output from parser.parse_resume() with keys: skills, education, experience, name, etc.
        interests: Optional career interests text.
    """
    return recommend_career_paths(
        skills=parsed_resume.get('skills', []),
        education=parsed_resume.get('education', []),
        experience=parsed_resume.get('experience', []),
        projects=parsed_resume.get('projects', []),
        interests=interests,
    )
