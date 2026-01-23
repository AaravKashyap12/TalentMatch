# TalentMatch 🎯

### AI-Powered Resume Screening & Candidate Ranking Platform

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React-Frontend-61DAFB)
![NLP](https://img.shields.io/badge/NLP-spaCy-09A3D5)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

**TalentMatch** is a full-stack, AI-driven **Applicant Tracking & Resume Intelligence system** built for modern **Computer Science & Engineering hiring**.

Unlike naive keyword-based ATS tools, TalentMatch combines:

- **NLP-based parsing**
- **Section-aware experience extraction**
- **Weighted, explainable scoring**
- **Recruiter-controlled ranking priorities**

The system is architected as a **cleanly separated platform**:

- **FastAPI backend** → authoritative scoring & ML logic
- **React + Tailwind frontend** → production-grade UI
- **Reusable ML core** → independent of UI or transport layer

---

## Core Capabilities

### 🧠 Intelligent Resume Parsing

- Section-aware extraction (Experience ≠ Projects ≠ Education)
- Robust date parsing (`2019–Present`, `Jan 2020 – Mar 2023`, etc.)
- CS-specific skill ontology (Backend, DevOps, ML, Data, Cloud, Security)
- PDF-native parsing (no manual text cleanup required)

---

### ⚖️ Weighted Ranking Engine

Recruiters can dynamically control ranking behavior using **priority levels**:

| Factor          | Description                                             |
| --------------- | ------------------------------------------------------- |
| 🧠 Skills Match | Overlap with job-critical technical skills              |
| 📅 Experience   | Real professional experience (not inflated by projects) |
| 🎓 Education    | Degree relevance & level                                |
| 📝 Relevance    | Semantic similarity between JD and resume content       |

Each factor supports:
`Ignore · Low · Medium · High · Critical`

Scores are normalized into a **stable 0–100 match score**, regardless of configuration.

---

### 📊 ATS & Analytics

- **Final Match Score**
- **ATS Visibility Score**
- Component-level breakdown (Skills / Exp / Edu / Relevance)
- Aggregate metrics:
  - Top Match
  - Average Score
  - Total Candidates
  - Avg / Top / Median ATS

- Interactive comparison charts
- Full CSV export for offline review

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
│   ├── routes.py
│   ├── schemas.py
│   ├── constants.py
│   └── resume_parser.py
│
├── ml/               # Core ML / NLP logic (UI-agnostic)
│   ├── matcher.py
│   └── nlp_utils.py
│
├── web/              # React + Vite + Tailwind frontend
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── api.js
│   └── tailwind.config.js
│
├── test_real_resumes.py
│
├── requirements.txt
└── README.md
```

**Key design principle:**

> All business logic lives in the backend + ML layer.
> The frontend is a pure consumer of the API.

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
- ✅ ML scoring engine stable
- ✅ React UI feature-parity achieved
- ✅ Streamlit legacy UI retired
- 🔜 Deployment (Vercel + Render/Fly.io)
- 🔜 Authentication & saved analyses
- 🔜 Role-specific scoring presets

---

## Design Philosophy

- **Explainability > black-box scores**
- **Separation of concerns**
- **Backend-driven intelligence**
- **UI parity with real recruiter workflows**
- **Production-first architecture**
