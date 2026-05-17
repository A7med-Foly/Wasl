# Wasl — AI-Driven Career Guidance & Recruitment Platform

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/A7med-Foly/Wasl)

> **Wasl** (وصل) bridges the gap between academic learning and real-world industry requirements using AI-powered career guidance and intelligent recruitment tools.

## 🎯 Overview

Wasl is a graduation project that provides a unified AI platform for:

- **Students & Job Seekers** — Personalized career path recommendations, skill gap analysis, and structured learning plans.
- **HR & Employers** — AI-powered resume parsing and intelligent job matching to reduce candidate evaluation time.

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **Resume Parsing** | Upload a PDF resume → AI extracts name, skills, education, experience as structured JSON |
| 🔍 **Job Matching** | Semantic + skill-based matching against 765 real Egyptian market jobs (LinkedIn dataset) |
| 📊 **Skill Gap Analysis** | Compare candidate skills vs target role — identifies matched, missing, and inferred skills with a readiness score |
| 🛤️ **Career Path Recommendations** | AI generates 3–5 personalized career paths with fit scores, rationale, and next steps |
| 📚 **Learning Plans** | Week-by-week structured learning plans with courses, projects, and certifications |
| 🚀 **Full Pipeline** | All-in-one endpoint: Parse → Match → Analyze → Recommend → Plan |

## 🏗️ Architecture

```
Wasl/
├── data/
│   ├── jobs.json                    # 765 real LinkedIn jobs (Egyptian market)
│   └── resumes/                     # Sample CVs
├── scripts/
│   └── process_linkedin_jobs.py     # LinkedIn data ETL
├── wasl_ai/
│   └── src/
│       ├── api.py                   # FastAPI (10 endpoints)
│       ├── parser.py                # Resume PDF parser (LLM)
│       ├── matcher.py               # Job matcher (semantic + skill overlap)
│       ├── skill_analyzer.py        # Skill gap analysis engine
│       ├── career_advisor.py        # Career path recommendations
│       └── learning_planner.py      # Learning plan generator
├── .env                             # API keys
├── expose_api.py                    # Ngrok tunnel for remote testing
└── requirements.txt                 # Dependencies
```

## 🚀 Quick Start

### 1. Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure
Create a `.env` file:
```
OPENROUTER_API_KEY=your-key-here
```

### 3. Run
```bash
uvicorn wasl_ai.src.api:app --reload --host 0.0.0.0 --port 8000
```

### 4. Explore
Open **Swagger UI** at: [http://localhost:8000/docs](http://localhost:8000/docs)

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/resume/parse` | Parse a PDF resume into structured JSON |
| `POST` | `/jobs/match` | Match resume against job database |
| `GET` | `/jobs/list` | List jobs with filtering & pagination |
| `GET` | `/jobs/domains` | List available job domains |
| `POST` | `/skills/analyze` | Skill gap analysis vs a target role |
| `POST` | `/career/recommend` | AI career path recommendations |
| `POST` | `/learning/plan` | Generate a learning plan |
| `POST` | `/resume/full-analysis` | Full pipeline (all-in-one) |
| `GET` | `/health` | Health check |