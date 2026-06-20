"""
Learning Plan Generator for Wasl.

Takes skill gap analysis output and generates a structured, week-by-week
learning plan with specific resources, projects, and milestones.
"""
import os
import json
from typing import List, Dict, Any, Optional
from wasl_ai.src.config import settings
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field


# --- Output Schema ---

class LearningResource(BaseModel):
    type: str = Field(description="Resource type: 'course', 'documentation', 'tutorial', 'book', 'project', 'certification'")
    name: str = Field(description="Name of the resource")
    provider: str = Field(description="Platform or provider (e.g., 'Coursera', 'YouTube', 'Udemy', 'freeCodeCamp')")
    url: str = Field(description="URL to the resource (use real, verifiable URLs when possible)")
    free: bool = Field(description="Whether the resource is free")
    estimated_hours: int = Field(description="Estimated hours to complete")


class LearningWeek(BaseModel):
    week: str = Field(description="Week range (e.g., '1-2', '3-4')")
    focus: str = Field(description="Main topic/skill focus for this period")
    learning_objectives: List[str] = Field(description="2-4 specific learning objectives")
    resources: List[LearningResource] = Field(description="2-4 recommended resources")
    practice_project: str = Field(description="A hands-on mini-project to practice what was learned")
    milestone: str = Field(description="What the candidate should be able to do by the end of this week")


class LearningPlan(BaseModel):
    target_role: str = Field(description="The role this plan prepares the candidate for")
    current_level: str = Field(description="Candidate's current level: 'beginner', 'intermediate', 'advanced'")
    total_duration: str = Field(description="Total estimated duration (e.g., '12 weeks')")
    weekly_hours: int = Field(description="Recommended study hours per week")
    plan: List[LearningWeek] = Field(description="Week-by-week learning plan")
    certifications: List[str] = Field(description="Recommended certifications to pursue")
    portfolio_projects: List[str] = Field(description="2-3 portfolio project ideas to showcase skills")
    tips: List[str] = Field(description="3-5 practical tips for the learning journey")


# --- LLM Setup ---

def _get_llm():
    """Initialize the LLM via OpenRouter."""
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set in configuration/environment")
    
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LEARNING_PLANNER_TEMPERATURE,
        api_key=api_key,
        base_url=settings.LLM_BASE_URL
    )


# --- Core Generation ---

def generate_learning_plan(
    target_role: str,
    current_skills: List[str],
    missing_skills: List[str],
    candidate_education: Optional[List[str]] = None,
    candidate_experience: Optional[List[str]] = None,
    weekly_hours: int = 15,
) -> Dict[str, Any]:
    """
    Generate a structured learning plan to close skill gaps.
    
    Args:
        target_role: The target career role.
        current_skills: Skills the candidate already has.
        missing_skills: Skills the candidate needs to develop.
        candidate_education: Education background for context.
        candidate_experience: Experience for context.
        weekly_hours: How many hours per week the candidate can study.
    
    Returns:
        Dict matching LearningPlan schema.
    """
    llm = _get_llm()
    parser = JsonOutputParser(pydantic_object=LearningPlan)
    
    education_str = ', '.join(candidate_education) if candidate_education else 'Not specified'
    experience_str = ', '.join(candidate_experience) if candidate_experience else 'Fresh graduate / No experience'
    
    prompt = PromptTemplate(
        template="""You are an expert Learning Path Designer for tech careers, with knowledge of the best online resources available in 2025-2026.

Create a detailed, structured learning plan for this candidate.

CANDIDATE:
- Current Skills: {current_skills}
- Education: {education}
- Experience: {experience}
- Available study time: {weekly_hours} hours/week

TARGET ROLE: {target_role}
SKILLS TO DEVELOP: {missing_skills}

GUIDELINES:
1. Prioritize the most critical skills first in the plan timeline.
2. Each week should build on the previous weeks.
3. Include a mix of theory and hands-on practice.
4. Prefer FREE resources when available (YouTube, freeCodeCamp, Coursera audit, documentation).
5. Include platform-specific resources when relevant:
   - Coursera, Udemy, YouTube channels, official docs, Kaggle, LeetCode
6. Each week must have a concrete practice project (not just "do exercises").
7. Recommend certifications that are valued in the Egyptian/MENA market:
   - AWS Certified, Google Cloud, Azure, Meta certifications, etc.
8. Portfolio projects should be impressive enough for job applications.
9. Be realistic with timelines based on the candidate's weekly hours.
10. Use REAL resource names and providers (not made-up ones).

{format_instructions}
""",
        input_variables=["current_skills", "education", "experience", "weekly_hours", "target_role", "missing_skills"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    chain = prompt | llm | parser
    
    try:
        result = chain.invoke({
            "current_skills": ', '.join(current_skills) if current_skills else 'None',
            "education": education_str,
            "experience": experience_str,
            "weekly_hours": str(weekly_hours),
            "target_role": target_role,
            "missing_skills": ', '.join(missing_skills) if missing_skills else 'General role skills',
        })
        return result
    except Exception as e:
        print(f"Error generating learning plan: {e}")
        return {
            "target_role": target_role,
            "current_level": "unknown",
            "total_duration": "unknown",
            "weekly_hours": weekly_hours,
            "plan": [],
            "certifications": [],
            "portfolio_projects": [],
            "tips": [],
            "error": str(e),
        }


def generate_plan_from_gap_analysis(
    gap_result: Dict[str, Any],
    candidate_education: Optional[List[str]] = None,
    candidate_experience: Optional[List[str]] = None,
    weekly_hours: int = 15,
) -> Dict[str, Any]:
    """
    Convenience: generate a learning plan directly from skill gap analysis output.
    """
    missing = gap_result.get('missing_critical', []) + gap_result.get('missing_nice_to_have', [])
    current = gap_result.get('matched_skills', []) + gap_result.get('bonus_skills', [])
    
    return generate_learning_plan(
        target_role=gap_result.get('target_role', 'Software Engineer'),
        current_skills=current,
        missing_skills=missing,
        candidate_education=candidate_education,
        candidate_experience=candidate_experience,
        weekly_hours=weekly_hours,
    )
