# TalentMatch

TalentMatch is an AI-assisted resume screening platform for recruiters and hiring teams. It helps turn a job description and a batch of resumes into a ranked, explainable candidate shortlist.

## What It Does

- Upload multiple resume PDFs for a role
- Paste or write a job description
- Separate required skills from preferred skills
- Rank candidates by overall match score
- Show matched skills, missing required skills, experience, education, ATS quality, and role relevance
- Explain why a candidate scored well or needs review
- Compare candidates side by side
- Track previous scans in scan history
- Limit each account to 5 free scans

## Why TalentMatch

Traditional resume screening tools often behave like keyword checkers. TalentMatch is designed to be more context-aware:

- Required and preferred skills are handled separately
- Backend frameworks, cloud platforms, APIs, databases, and related skills are grouped intelligently
- Inferred matches have lower confidence than explicit resume evidence
- Stack mismatch is considered when the job and resume emphasize different technologies
- Recommendations are explained instead of shown as random scores

## Core Screens

### Dashboard

Shows recent scans, hiring signal, candidate volume, and next actions.

### New Scan

Create a screening run by adding:

- Role title
- Job description
- Required skills
- Preferred skills
- Resume PDFs
- Scoring priorities

### Results

Review ranked candidates with:

- Final score
- Hiring recommendation
- Confidence level
- Matched skills
- Missing required skills
- AI overview
- Score breakdown

### Compare

Compare candidates side by side across skills, score dimensions, recommendations, and concerns.

### History

Revisit past scans and open previous results.

### Admin Analytics

A developer-only dashboard for platform usage and scan analytics. It is protected by an admin secret.

## AI Assistance

TalentMatch can use Groq with `llama-3.1-8b-instant` for:

- Job description skill-tier parsing
- Candidate overview summaries

If no Groq API key is configured, the deterministic matching system still works.

## Account Limits

Each account gets 5 free scans. In local development mode, the limit can be bypassed for testing.

## Tech Stack

- React + Vite frontend
- FastAPI backend
- PostgreSQL production database
- SQLAlchemy async ORM
- Supabase Auth
- Groq optional AI integration
- spaCy, TF-IDF, and custom skill ontology for matching

## Project Status

TalentMatch is built as a production-ready MVP for AI-assisted recruiting workflows.
