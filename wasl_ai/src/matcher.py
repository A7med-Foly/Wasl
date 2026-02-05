import json
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any

# Global model cache to avoid reloading on every request
_model = None
_job_embeddings = None
_jobs_data = None

MODEL_NAME = 'all-MiniLM-L6-v2'
JOBS_FILE = 'data/jobs.json'

def get_model():
    global _model
    if _model is None:
        print("Loading Sentence Transformer Model...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def load_jobs():
    global _jobs_data, _job_embeddings
    
    if _jobs_data is not None:
        return _jobs_data, _job_embeddings

    if not os.path.exists(JOBS_FILE):
        print(f"Warning: {JOBS_FILE} not found.")
        return [], None

    with open(JOBS_FILE, 'r') as f:
        _jobs_data = json.load(f)

    # create a text representation for each job to embed
    # strictly combined title + skills + description
    job_texts = [
        f"{job['title']} {' '.join(job['skills'])} {job['description']}" 
        for job in _jobs_data
    ]
    
    model = get_model()
    _job_embeddings = model.encode(job_texts)
    
    return _jobs_data, _job_embeddings

def match_resume_to_jobs(resume_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Matches a resume text against the loaded jobs using cosine similarity.
    """
    if not resume_text:
        return []

    jobs, job_embeddings = load_jobs()
    if not jobs or job_embeddings is None:
        return []

    model = get_model()
    resume_embedding = model.encode([resume_text])
    
    # Calculate Cosine Similarity
    # resume_embedding is (1, 384), job_embeddings is (N, 384)
    similarities = cosine_similarity(resume_embedding, job_embeddings)[0]
    
    # Get top_k indices
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    results = []
    for idx in top_indices:
        score = float(similarities[idx])
        results.append({
            "job": jobs[idx],
            "score": round(score, 2)  # 0.0 to 1.0
        })
        
    return results
