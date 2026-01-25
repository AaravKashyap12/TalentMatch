# TalentMatch 🎯

### NLP-Powered Resume Screening & Candidate Ranking Platform

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React-Frontend-61DAFB)
![NLP](https://img.shields.io/badge/NLP-spaCy-09A3D5)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

**TalentMatch** is a full-stack, **NLP-driven Applicant Tracking & Resume Intelligence system** built for modern **Computer Science & Engineering hiring**.

Unlike opaque "AI" black-box tools, TalentMatch uses a **transparent, deterministic scoring engine** combining:

- **Linguistic Parsing**: Spacy-based NLP for accurate text cleaning and lemmatization.
- **Statistical Matching**: TF-IDF vector space modeling to measure semantic relevance.
- **Heuristic Extraction**: Robust Regex patterns for precision extraction of years of experience and education.
- **Weighted Logic**: Explainable, recruiter-defined scoring priorities.

The system is architected as a **cleanly separated platform**:

- **FastAPI backend** → Authoritative scoring & ML logic
- **React + Tailwind frontend** → Production-grade UI
- **Reusable ML core** → Independent of UI or transport layer

---

## Core Capabilities

### 🧠 Intelligent Parsing Engine

- **Deterministic Extraction**: Uses pattern matching rules to verify Experience vs. Projects vs. Education (preventing "fake" experience).
- **Robust Date Parsing**: Normalizes diverse date formats (`2019–Present`, `Jan 2020 – Mar 2023`) to calculate exact tenure.
- **CS-Specific Ontology**: Specialized in detecting technical stacks (Backend, DevOps, ML, Data, Cloud).
- **PDF-Native**: Extracts raw text directly from PDF binary streams.

---

### ⚖️ Weighted Ranking Engine

Recruiters can dynamically control ranking behavior using **priority levels**. The system calculates a final score based on a weighted sum of four deterministic components:

| Factor          | Method                                                  | Description                                             |
| --------------- | ------------------------------------------------------- | ------------------------------------------------------- |
| 🧠 Skills Match | **Set Intersection**                                    | Exact overlap with job-critical technical skills        |
| 📅 Experience   | **Regex Heuristics**                                    | Calculated professional tenure (years)                  |
| 🎓 Education    | **Keyword Matching**                                    | Degree level detection (PhD > Master > Bachelor)        |
| 📝 Relevance    | **TF-IDF Cosine Similarity**                            | Statistical similarity between Resume and JD text       |

Each factor supports:
`Ignore · Low · Medium · High · Critical`

Scores are normalized into a **stable 0–100 match score**, providing full explainability for every ranking decision.

---

### 📊 ATS & Analytics

- **Final Match Score**: Aggregated weighted score.
- **ATS Visibility Score**: Heuristic check for keyword density and formatting parsing friendliness.
- **Deep-Dive Metrics**: Breakdown of Skills, Experience, Education, and Relevance scores.
- **Interactive Charts**: Visual comparison of candidates.
- **CSV Export**: Full data dump for offline analysis.

---

### 🧾 Resume Review UX

- Horizontally scrollable, dense ranking table
- Fixed candidate column for large datasets
- Expandable matched-skills display
- Deterministic ordering (highest match first)
- Designed to scale beyond 20+ candidates

---

## Architecture

```
TalentMatch/
├── api/              # FastAPI application (API contract)
│   ├── main.py
│   ├── routes.py     # Endpoints orchestration
│   └── resume_parser.py # PyPDF2 extraction
│
├── ml/               # Core Logic
│   ├── matcher.py    # Scoring Engine (Regex + TF-IDF)
│   └── nlp_utils.py  # Spacy text processing
│
├── web/              # React + Vite + Tailwind frontend
│   ├── src/
│   │   ├── pages/
│   │   └── components/
│   └── tailwind.config.js
│
├── requirements.txt
└── README.md
```

**Key design principle:**

> **No hallucinations.** The system provides raw, evidence-based metrics, not generative summaries.

---

## API Overview

### `POST /api/v1/scan/pdf`

Analyzes a batch of resumes against a job description.

**Input**

- Job description (text)
- Priority levels (skills / experience / education / relevance)
- One or more PDF resumes

**Output**

- Per-candidate:
  - Final score
  - ATS score
  - Component scores
  - Matched skills
  - Experience summary

The API is **stable and versioned**, making it safe for multiple clients.

---

## Local Setup

### Backend (FastAPI)

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm

python -m uvicorn api.main:app --reload
```

API available at:
`http://127.0.0.1:8000/docs`

---

### Frontend (React)

```bash
cd web
npm install
npm run dev
```

Frontend available at:
`http://localhost:5173`

---

## Development Status

- ✅ Backend API complete
- ✅ Scoring engine stable (TF-IDF/Regex)
- ✅ React UI feature-parity achieved
- 🔜 Deployment (Vercel + Render/Fly.io)
- 🔜 Authentication & saved analyses

---

## Design Philosophy

- **Explainability > "Magic"**
- **Deterministic scoring**
- **Backend-driven intelligence**
- **Production-first architecture**
