"""
Job Matching Engine for Wasl.

Uses sentence-transformers (all-MiniLM-L6-v2) to compute semantic similarity
between a candidate's resume/skills and job postings from the LinkedIn dataset.

Supports filtering by domain, experience level, and a composite scoring approach
that blends semantic similarity with explicit skill overlap.
"""
import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Optional

# Global model cache to avoid reloading on every request
_model = None
_job_embeddings = None
_jobs_data = None

MODEL_NAME = 'all-MiniLM-L6-v2'
JOBS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'jobs.json')


def get_model():
    """Get or lazily load the sentence transformer model."""
    global _model
    if _model is None:
        print("Loading Sentence Transformer Model...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def load_jobs(force_reload: bool = False):
    """Load jobs from JSON and pre-compute embeddings."""
    global _jobs_data, _job_embeddings
    
    if _jobs_data is not None and not force_reload:
        return _jobs_data, _job_embeddings

    if not os.path.exists(JOBS_FILE):
        print(f"Warning: {JOBS_FILE} not found.")
        return [], None

    with open(JOBS_FILE, 'r', encoding='utf-8') as f:
        _jobs_data = json.load(f)

    # Create a rich text representation for each job
    job_texts = []
    for job in _jobs_data:
        skills_str = ' '.join(job.get('skills', []))
        text = f"{job['title']} {skills_str} {job.get('description', '')}"
        job_texts.append(text)
    
    model = get_model()
    print(f"Encoding {len(job_texts)} job postings...")
    _job_embeddings = model.encode(job_texts, show_progress_bar=False)
    print("Job embeddings ready.")
    
    return _jobs_data, _job_embeddings


def _compute_skill_overlap(resume_skills: List[str], job_skills: List[str]) -> float:
    """
    Compute the fraction of job skills matched by the candidate.
    Uses case-insensitive partial matching.
    Returns 0.0-1.0
    """
    if not job_skills:
        return 0.0
    
    resume_lower = {s.lower().strip() for s in resume_skills}
    matched = 0
    for js in job_skills:
        js_lower = js.lower().strip()
        # Exact match or substring match
        if js_lower in resume_lower or any(js_lower in rs or rs in js_lower for rs in resume_lower):
            matched += 1
    
    return matched / len(job_skills)


def match_resume_to_jobs(
    resume_text: str,
    resume_skills: Optional[List[str]] = None,
    top_k: int = 5,
    domain_filter: Optional[str] = None,
    experience_filter: Optional[str] = None,
    semantic_weight: float = 0.6,
    skill_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Match a resume against the job database.
    
    Uses a composite score:
      composite = semantic_weight * cosine_sim + skill_weight * skill_overlap
    
    Args:
        resume_text: Full text or skill summary of the candidate.
        resume_skills: Optional explicit list of skills for skill-overlap scoring.
        top_k: Number of top matches to return.
        domain_filter: If set, only consider jobs in this domain.
        experience_filter: If set, only consider jobs at this level (intern/junior/mid/senior).
        semantic_weight: Weight for semantic similarity (default 0.6).
        skill_weight: Weight for explicit skill overlap (default 0.4).
    
    Returns:
        List of dicts with 'job' and 'score' keys, sorted by score descending.
    """
    if not resume_text:
        return []

    jobs, job_embeddings = load_jobs()
    if not jobs or job_embeddings is None:
        return []

    model = get_model()
    resume_embedding = model.encode([resume_text])
    
    # Cosine similarity: (1, N) → (N,)
    similarities = cosine_similarity(resume_embedding, job_embeddings)[0]
    
    results = []
    for idx, job in enumerate(jobs):
        # Apply filters
        if domain_filter and job.get('domain', '').lower() != domain_filter.lower():
            continue
        if experience_filter and job.get('experience_level', '').lower() != experience_filter.lower():
            continue
        
        semantic_score = float(similarities[idx])
        
        # Compute skill overlap if resume_skills provided
        if resume_skills and job.get('skills'):
            skill_score = _compute_skill_overlap(resume_skills, job['skills'])
            composite = semantic_weight * semantic_score + skill_weight * skill_score
        else:
            composite = semantic_score
        
        results.append({
            'job': {
                'id': job.get('id'),
                'title': job.get('title'),
                'company': job.get('company'),
                'description': job.get('description', '')[:500],  # Truncate for response
                'skills': job.get('skills', []),
                'experience_level': job.get('experience_level', ''),
                'domain': job.get('domain', ''),
                'location': job.get('location', ''),
                'employment_type': job.get('employment_type', ''),
                'workplace': job.get('workplace', ''),
            },
            'score': round(composite, 3),
            'semantic_score': round(semantic_score, 3),
            'skill_overlap': round(
                _compute_skill_overlap(resume_skills, job.get('skills', [])) if resume_skills else 0.0, 3
            ),
        })
    
    # Sort by composite score descending
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:top_k]


def get_all_jobs(
    domain: Optional[str] = None,
    experience_level: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    List all jobs with optional filtering and pagination.
    """
    jobs, _ = load_jobs()
    
    filtered = jobs
    if domain:
        filtered = [j for j in filtered if j.get('domain', '').lower() == domain.lower()]
    if experience_level:
        filtered = [j for j in filtered if j.get('experience_level', '').lower() == experience_level.lower()]
    
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    page_jobs = filtered[start:end]
    
    return {
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size,
        'jobs': page_jobs,
    }


def get_available_domains() -> List[str]:
    """Return a list of unique domains in the job database."""
    jobs, _ = load_jobs()
    return sorted(set(j.get('domain', 'Other') for j in jobs))


# ═══════════════════════════════════════════
#  DYNAMIC MATCHING (Firebase Jobs)
# ═══════════════════════════════════════════

# Cache: { job_id_str: embedding_vector }
_dynamic_embedding_cache: Dict[str, Any] = {}


def _get_job_text(job: Dict[str, Any]) -> str:
    """Build a text representation for embedding from a job dict."""
    skills_str = ' '.join(job.get('skills', []))
    return f"{job.get('title', '')} {skills_str} {job.get('description', '')}"


def match_resume_to_provided_jobs(
    resume_text: str,
    jobs: List[Dict[str, Any]],
    resume_skills: Optional[List[str]] = None,
    top_k: int = 5,
    semantic_weight: float = 0.6,
    skill_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Match a resume against a list of jobs provided by the client (e.g., from Firebase).

    Uses the SAME sentence-transformer + skill-overlap logic as match_resume_to_jobs,
    but caches embeddings by job ID so only new/unseen jobs get computed.

    Args:
        resume_text: Full text or skill summary of the candidate.
        jobs: List of job dicts from Firebase (must have 'id', 'title', 'skills', 'description').
        resume_skills: Optional explicit list of skills for skill-overlap scoring.
        top_k: Number of top matches to return.
        semantic_weight: Weight for semantic similarity (default 0.6).
        skill_weight: Weight for explicit skill overlap (default 0.4).

    Returns:
        List of dicts with 'job' and 'score' keys, sorted by score descending.
    """
    global _dynamic_embedding_cache

    if not resume_text or not jobs:
        return []

    model = get_model()

    # --- Build embeddings (cache-aware) ---
    job_embeddings_list = []
    new_jobs_to_encode = []  # (index, job_id, text)
    
    for idx, job in enumerate(jobs):
        job_id = str(job.get('id', idx))
        if job_id in _dynamic_embedding_cache:
            job_embeddings_list.append((idx, _dynamic_embedding_cache[job_id]))
        else:
            new_jobs_to_encode.append((idx, job_id, _get_job_text(job)))

    # Batch-encode only the NEW jobs
    if new_jobs_to_encode:
        new_texts = [item[2] for item in new_jobs_to_encode]
        new_embeddings = model.encode(new_texts, show_progress_bar=False)
        for i, (idx, job_id, _) in enumerate(new_jobs_to_encode):
            _dynamic_embedding_cache[job_id] = new_embeddings[i]
            job_embeddings_list.append((idx, new_embeddings[i]))

    # Sort by original index to maintain order
    job_embeddings_list.sort(key=lambda x: x[0])
    all_embeddings = np.array([emb for _, emb in job_embeddings_list])

    # --- Score ---
    resume_embedding = model.encode([resume_text])
    similarities = cosine_similarity(resume_embedding, all_embeddings)[0]

    results = []
    for i, (idx, _) in enumerate(job_embeddings_list):
        job = jobs[idx]
        semantic_score = float(similarities[i])

        if resume_skills and job.get('skills'):
            skill_score = _compute_skill_overlap(resume_skills, job['skills'])
            composite = semantic_weight * semantic_score + skill_weight * skill_score
        else:
            composite = semantic_score

        # Return all original fields of the job object (preserving companyId, companyImg, requirments, etc. for Flutter)
        job_res = dict(job)
        job_res['id'] = str(job.get('id', ''))
        # Ensure description is a string (and not None)
        job_res['description'] = job.get('description', '')

        results.append({
            'job': job_res,
            'score': round(composite, 3),
            'semantic_score': round(semantic_score, 3),
            'skill_overlap': round(
                _compute_skill_overlap(resume_skills, job.get('skills', [])) if resume_skills else 0.0, 3
            ),
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]

