import re

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_experience(text: str) -> float:
    matches = re.findall(r'(\d+)\+?\s+years', text.lower())
    if not matches:
        return 0.0
    return float(max(matches))


def parse_resume(resume_text: str):
    cleaned = clean_text(resume_text)
    
    # Simple keyword-based skill extraction
    from pipeline.skills import SKILL_SYNONYMS
    found_skills = []
    text_lower = cleaned.lower()
    for main, variants in SKILL_SYNONYMS.items():
        if main in text_lower:
            found_skills.append(main)
        else:
            for v in variants:
                if v in text_lower:
                    found_skills.append(main)
                    break

    return {
        "raw_text": resume_text,
        "cleaned_text": cleaned,
        "skills": list(set(found_skills)),
        "experience_years": extract_experience(cleaned),
        "education": [],
        
        # DEFAULT SAFE SCORES (IMPORTANT)
        "skill_score": 0.5,
        "experience_score": min(extract_experience(cleaned) / 5, 1.0),
        "ats_score": 0.7
    }
