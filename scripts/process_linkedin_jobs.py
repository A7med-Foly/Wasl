"""
Process raw LinkedIn jobs dataset into a clean, standardized format for Wasl.
Reads from data/linkedin_jobs_raw.json and outputs data/jobs.json
"""
import json
import os
import hashlib
from collections import Counter

RAW_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'linkedin_jobs_raw.json')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'jobs.json')

# Map LinkedIn experience levels to our standardized levels
EXPERIENCE_MAP = {
    'Entry level': 'junior',
    'Associate': 'junior',
    'Internship': 'intern',
    'Mid-Senior level': 'mid',
    'Director': 'senior',
    'Executive': 'senior',
    '': 'junior',  # default
}

# Domain classification based on keywords in title/description
DOMAIN_KEYWORDS = {
    'Software Engineering': [
        'software engineer', 'developer', 'full stack', 'fullstack', 'frontend',
        'front-end', 'backend', 'back-end', 'web developer', 'application developer',
        'java developer', 'python developer', '.net developer', 'react developer',
        'angular developer', 'node.js', 'software development',
    ],
    'Mobile Development': [
        'mobile', 'flutter', 'ios', 'android', 'react native', 'kotlin', 'swift',
    ],
    'Data Science & Analytics': [
        'data scientist', 'data analyst', 'analytics', 'business intelligence',
        'bi developer', 'power bi', 'tableau', 'data analytics', 'statistician',
    ],
    'Machine Learning & AI': [
        'machine learning', 'deep learning', 'ai engineer', 'artificial intelligence',
        'nlp', 'computer vision', 'ml engineer', 'data science', 'neural network',
    ],
    'Data Engineering': [
        'data engineer', 'etl', 'data pipeline', 'data integration', 'airflow',
        'spark', 'big data', 'data warehouse', 'data lake',
    ],
    'DevOps & Cloud': [
        'devops', 'cloud', 'aws', 'azure', 'gcp', 'kubernetes', 'docker',
        'infrastructure', 'sre', 'site reliability', 'platform engineer',
        'cicd', 'ci/cd',
    ],
    'Cybersecurity': [
        'security', 'cybersecurity', 'penetration', 'soc', 'threat',
        'vulnerability', 'infosec', 'information security', 'network security',
    ],
    'Networking & IT': [
        'network engineer', 'system admin', 'it support', 'technical support',
        'help desk', 'it engineer', 'systems engineer', 'network admin',
    ],
    'UI/UX Design': [
        'ui', 'ux', 'user experience', 'user interface', 'product design',
        'graphic design', 'figma', 'adobe xd',
    ],
    'Product Management': [
        'product manager', 'product owner', 'scrum master', 'agile', 'project manager',
    ],
    'QA & Testing': [
        'qa', 'quality assurance', 'test engineer', 'automation test', 'manual test',
        'selenium', 'testing',
    ],
    'Sales & Marketing': [
        'sales', 'marketing', 'business development', 'account manager',
        'digital marketing', 'seo', 'content', 'copywriter',
    ],
    'Customer Service': [
        'customer service', 'customer support', 'call center', 'customer care',
    ],
    'Other': [],
}


def classify_domain(title: str, description: str) -> str:
    """Classify a job into a domain based on title and description keywords."""
    text = f"{title} {description}".lower()
    
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if domain == 'Other':
            continue
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[domain] = score
    
    if scores:
        return max(scores, key=scores.get)
    return 'Other'


def clean_job(raw_job: dict, idx: int) -> dict:
    """Transform a raw LinkedIn job into our clean schema."""
    title = raw_job.get('title', '').strip()
    company = raw_job.get('companyName', '').strip()
    description = raw_job.get('descriptionText', '').strip()
    location = raw_job.get('formattedLocation', raw_job.get('location', '')).strip()
    
    # Skills
    skills = raw_job.get('skills', [])
    if not isinstance(skills, list):
        skills = []
    skills = [s.strip() for s in skills if isinstance(s, str) and s.strip()]
    
    # Experience level
    raw_level = raw_job.get('formattedExperienceLevel', '')
    experience_level = EXPERIENCE_MAP.get(raw_level, 'junior')
    
    # Employment type
    employment_type = raw_job.get('formattedEmploymentStatus', 'Full-time')
    
    # Domain
    domain = classify_domain(title, description)
    
    # Industries
    industries = raw_job.get('formattedIndustries', [])
    if not isinstance(industries, list):
        industries = []
    
    # Workplace type
    workplace_types = raw_job.get('workplaceTypes', [])
    workplace = workplace_types[0] if workplace_types else 'On-site'
    
    # Truncate description to keep file size manageable
    if len(description) > 1500:
        description = description[:1500] + '...'
    
    return {
        'id': idx + 1,
        'title': title,
        'company': company,
        'description': description,
        'skills': skills,
        'experience_level': experience_level,
        'domain': domain,
        'location': location,
        'employment_type': employment_type,
        'workplace': workplace,
        'industries': industries,
        'linkedin_url': raw_job.get('link', ''),
    }


def process():
    """Main processing pipeline."""
    print(f"Reading raw data from {RAW_FILE}...")
    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    print(f"Total raw jobs: {len(raw_data)}")
    
    # Filter: must have title, description, and at least 1 skill
    valid_jobs = [
        j for j in raw_data
        if j.get('title', '').strip()
        and j.get('descriptionText', '').strip()
        and len(j.get('skills', [])) >= 1
    ]
    print(f"Jobs with title + description + skills: {len(valid_jobs)}")
    
    # Deduplicate by title + company
    seen = set()
    unique_jobs = []
    for j in valid_jobs:
        key = f"{j['title'].lower().strip()}|{j.get('companyName', '').lower().strip()}"
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)
    print(f"After deduplication: {len(unique_jobs)}")
    
    # Clean and transform
    cleaned = [clean_job(j, idx) for idx, j in enumerate(unique_jobs)]
    
    # Stats
    domain_counts = Counter(j['domain'] for j in cleaned)
    level_counts = Counter(j['experience_level'] for j in cleaned)
    
    print(f"\nDomain distribution:")
    for domain, count in domain_counts.most_common():
        print(f"  {domain}: {count}")
    
    print(f"\nExperience level distribution:")
    for level, count in level_counts.most_common():
        print(f"  {level}: {count}")
    
    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Wrote {len(cleaned)} jobs to {OUTPUT_FILE}")


if __name__ == '__main__':
    process()
