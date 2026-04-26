from pipeline.parser import parse_resume
from pipeline.skills import extract_skills, skill_match_score, identify_missing_skills
from pipeline.embeddings import semantic_similarity
from pipeline.scoring import compute_base_score


def process_candidate(resume_text, jd_text, candidate_name="Candidate"):
    
    # STEP 1: Parse
    parsed = parse_resume(resume_text)

    # STEP 2: Skills (IMPORTANT FIX)
    extracted_skills = extract_skills(parsed["skills"])

    skill_score = skill_match_score(extracted_skills, jd_text)
    missing_skills = identify_missing_skills(extracted_skills, jd_text)

    # STEP 3: Other Scores
    exp_score = parsed["experience_score"]
    semantic_score = semantic_similarity(resume_text, jd_text)
    ats_score = parsed["ats_score"]

    # STEP 4: Final Score
    base_score = compute_base_score(
        skill_score,
        exp_score,
        semantic_score,
        ats_score
    )

    return {
        "name": candidate_name,
        "score": base_score,
        "matched_skills": extracted_skills,
        "missing": missing_skills,
        "breakdown": {
            "skills": skill_score,
            "experience": exp_score,
            "semantic": semantic_score,
            "ats": ats_score
        }
    }
