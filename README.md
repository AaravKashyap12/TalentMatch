# TalentMatch

> **AI-powered resume screening that ranks candidates by evidence, not keywords.**

TalentMatch turns a job description and a batch of resumes into a ranked, explainable shortlist — in minutes, not hours.

---

## What It Does

Upload resumes. Paste a job description. Get a ranked shortlist with scores you can actually explain to a hiring committee.

| Capability | Detail |
|---|---|
| **Multi-resume upload** | Batch-process PDF resumes for any role |
| **Structured JD parsing** | Separate required vs. preferred skills automatically |
| **Candidate ranking** | Scored by overall match — not keyword frequency |
| **Score breakdown** | Skills matched, missing requirements, experience, education, ATS quality, role relevance |
| **AI overviews** | Plain-language explanation of why a candidate scored well or needs review |
| **Side-by-side compare** | Compare any two candidates across all dimensions |
| **Scan history** | Revisit and reopen any past screening run |
| **Account limits** | 5 free scans per account; bypass available in local dev |

---

## Why TalentMatch

Most resume tools are fancy keyword matchers. TalentMatch is designed to be context-aware:

- **Required vs. preferred skills are handled separately** — a missing required skill hurts more than a missing preferred one
- **Skill grouping is intelligent** — backend frameworks, cloud platforms, databases, and related tools are clustered semantically
- **Inferred matches are marked lower confidence** than explicit resume evidence
- **Stack mismatch is flagged** — when the job emphasizes React and the resume only shows Angular, that gap surfaces
- **Recommendations are explained** — "Strong hire: 4/5 required skills matched, 6 years relevant experience, senior-level titles" beats a random percentage

---

## Screens

### Dashboard
Recent scans, hiring signal, candidate volume, and next actions at a glance.

### New Scan
Create a screening run:
- Role title
- Job description (paste or type)
- Required skills (hard requirements)
- Preferred skills (nice-to-haves)
- Resume PDFs (batch upload)
- Scoring priority weights

### Results
Review ranked candidates with:
- Final match score and hiring recommendation
- Confidence level (high / medium / low)
- Matched skills and missing required skills
- AI-generated candidate overview
- Full score breakdown by dimension

### Compare
Side-by-side candidate comparison across skills, score dimensions, recommendations, and red flags.

### History
All past scans with timestamps. Click any run to reopen its full results.

### Admin Analytics *(dev only)*
Platform usage, scan volume, and analytics. Protected by an admin secret — not exposed in production UI.

---

## AI Integration

TalentMatch uses **Groq** (`llama-3.1-8b-instant`) for two tasks:

1. **JD parsing** — extracts and tier-classifies skills from free-text job descriptions
2. **Candidate overviews** — generates concise, evidence-based summaries per candidate

If no Groq API key is configured, the deterministic matching pipeline runs fully without AI — scores, rankings, and breakdowns still work.

Set your key in `.env`:

```env
GROQ_API_KEY=your_key_here
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI |
| Database | PostgreSQL (production), SQLite (local dev) |
| ORM | SQLAlchemy (async) |
| Auth | Supabase Auth |
| AI | Groq (`llama-3.1-8b-instant`) — optional |
| NLP / Matching | spaCy, TF-IDF, custom skill ontology |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (or use the local SQLite fallback)
- Supabase project (for auth)
- Groq API key (optional — matching works without it)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in DATABASE_URL, SUPABASE_URL, SUPABASE_KEY, and optionally GROQ_API_KEY

uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install

cp .env.example .env.local
# Fill in VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_URL

npm run dev
```

App runs at `http://localhost:5173`. API at `http://localhost:8000`.

### Bypass scan limit (local dev)

Set `LOCAL_DEV_MODE=true` in your backend `.env` to disable the 5-scan limit during development.

---

## Matching Logic

TalentMatch uses a layered matching approach rather than simple keyword search:

1. **Skill extraction** — spaCy NER + a custom ontology maps resume text to canonical skill names
2. **Tier weighting** — required skill gaps are penalised significantly more than preferred gaps
3. **Semantic grouping** — skills are clustered by domain (e.g. `FastAPI → Python web framework → backend`)
4. **Confidence scoring** — explicit mentions score higher than inferred matches
5. **Stack mismatch penalty** — divergent technology stacks reduce the role relevance score
6. **Multi-dimension aggregation** — final score weights: skills (40%), experience (25%), role relevance (20%), education (10%), ATS quality (5%)

---

## Project Status

TalentMatch is a **production-ready MVP** built for AI-assisted recruiting workflows. Core features are stable. Planned work includes team collaboration, webhook integrations, and custom scoring weight presets per organization.

---

## License

MIT