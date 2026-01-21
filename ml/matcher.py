import re
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ============================================================
# SKILLS DATABASE
# ============================================================

SKILLS_DB = [
    # Languages
    "python", "java", "c++", "c", "c#", "javascript", "typescript", "go",
    "rust", "swift", "kotlin", "php", "ruby", "scala", "r", "matlab",

    # Web / Backend
    "html", "css", "react", "angular", "vue", "node.js", "next.js",
    "django", "flask", "fastapi", "spring boot",

    # Data / ML
    "machine learning", "deep learning", "data science", "nlp",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",

    # Cloud / DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "ci/cd", "linux", "git", "github",

    # Databases
    "sql", "nosql", "mongodb", "postgresql", "mysql", "redis",

    # CS Concepts
    "data structures", "algorithms", "system design", "oop"
]

# ============================================================
# SKILL EXTRACTION (NORMALIZED)
# ============================================================

def extract_skills(text):
    text = text.lower()
    found = set()

    for skill in SKILLS_DB:
        if len(skill) <= 3:
            pattern = rf"(?:^|\s){re.escape(skill)}(?:$|[\s,./])"
        else:
            pattern = rf"\b{re.escape(skill)}\b"

        if re.search(pattern, text):
            found.add(skill)

    return list(found)

# ============================================================
# EXPERIENCE EXTRACTION (STRICT)
# ============================================================

EXPERIENCE_HEADERS = [
    "experience", "work experience", "professional experience",
    "employment history", "work history"
]

STOP_HEADERS = [
    "education", "projects", "skills", "certifications",
    "achievements", "leadership", "interests", "summary"
]

def parse_date(date_str):
    date_str = date_str.strip().lower()
    if date_str in ["present", "current", "now"]:
        return datetime.now()
    
    # Try Month YYYY (e.g., "Jan 2020", "January 2020")
    # or MM/YYYY (01/2020)
    
    # Clean up
    date_str = re.sub(r"[,.]", "", date_str)
    
    try:
        # Match YYYY alone
        if re.match(r"^\d{4}$", date_str):
            return datetime(int(date_str), 1, 1)
        
        # Match MM/YYYY or MM-YYYY
        m = re.match(r"(\d{1,2})[/-](\d{4})", date_str)
        if m:
            return datetime(int(m.group(2)), int(m.group(1)), 1)
            
        # Match Month YYYY
        parts = date_str.split()
        if len(parts) >= 2:
            month_map = {
                "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
                "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
                "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
                "nov": 11, "november": 11, "dec": 12, "december": 12
            }
            month_str = parts[0][:3]
            year_str = parts[-1]
            if month_str in month_map and year_str.isdigit():
                return datetime(int(year_str), month_map[month_str], 1)

    except Exception:
        pass
        
    return None

def extract_experience(text):
    text = text.lower()
    start = None

    for h in EXPERIENCE_HEADERS:
        m = re.search(rf"(?:^|\n)\s*{h}\s*(?:\:)?\s*(?:\n|$)", text)
        if m:
            start = m.end()
            break

    if start is None:
        return ["0 Years"]

    end = len(text)
    for h in STOP_HEADERS:
        m = re.search(rf"(?:^|\n)\s*{h}\s*(?:\:)?\s*(?:\n|$)", text[start:])
        if m:
            end = start + m.start()
            break

    section = text[start:end]

    # Regex to capture date ranges
    # Matches:
    # 1. MM/YYYY - MM/YYYY
    # 2. Month YYYY - Month YYYY
    # 3. YYYY - YYYY
    # 4. ... - Present/Current
    
    date_pattern = r"((?:[a-zA-Z]+|\d{1,2})[/\s,.-]*\d{4}|\d{4})\s*[-–to]+(?:\s*)?((?:[a-zA-Z]+|\d{1,2})[/\s,.-]*\d{4}|\d{4}|present|current|now)"
    ranges = re.findall(date_pattern, section)

    total_months = 0

    for start_str, end_str in ranges:
        d1 = parse_date(start_str)
        d2 = parse_date(end_str)
        
        if d1 and d2 and d2 >= d1:
            diff = (d2.year - d1.year) * 12 + (d2.month - d1.month)
            total_months += max(1, diff) # At least 1 month if same month

    years = total_months / 12.0

    if years < 0.1:
        return ["0 Years"]

    return [f"{min(years, 40):.1f} Years"]

# ============================================================
# TEXT SIMILARITY
# ============================================================

def calculate_similarity(job_desc, resumes):
    if not resumes or not job_desc:
        return []

    docs = [job_desc] + resumes
    tfidf = TfidfVectorizer(stop_words="english")
    matrix = tfidf.fit_transform(docs)
    scores = cosine_similarity(matrix[0:1], matrix[1:])
    return scores[0].tolist()

# ============================================================
# WEIGHTED RANKING (UI SLIDERS)
# ============================================================

def calculate_component_scores(
    job_desc_clean,
    resumes_clean,
    job_desc_raw,
    resumes_raw,
    weights
):
    similarity_scores = calculate_similarity(job_desc_clean, resumes_clean)

    jd_skills = set(s.lower() for s in extract_skills(job_desc_raw))
    results = []

    for i, raw in enumerate(resumes_raw):
        resume_skills = set(s.lower() for s in extract_skills(raw))

        if jd_skills:
            overlap = jd_skills & resume_skills
            skills_score = len(overlap) / max(1, len(jd_skills))
        else:
            skills_score = min(1.0, len(resume_skills) / 8.0)

        exp_list = extract_experience(raw)
        years = 0.0
        for e in exp_list:
            m = re.search(r"(\d+(?:\.\d+)?)", e)
            if m:
                years = max(years, float(m.group(1)))

        exp_score = min(1.0, years / 10.0)

        edu_score = 0.5 if any(x in raw.lower() for x in [
            "bachelor", "master", "phd", "degree"
        ]) else 0.0

        raw_score = (
            weights["skills"] * skills_score +
            weights["experience"] * exp_score +
            weights["education"] * edu_score +
            weights["relevance"] * similarity_scores[i]
        )

        total_weight = sum(weights.values()) or 1.0
        final = raw_score / total_weight

        results.append({
            "final_score": round(final * 100, 2),
            "skills_score": round(skills_score * 100, 1),
            "exp_score": round(exp_score * 100, 1),
            "edu_score": round(edu_score * 100, 1),
            "relevance_score": round(similarity_scores[i] * 100, 1)
        })

    return results

# ============================================================
# ATS SCORE (CALIBRATED)
# ============================================================

def calculate_ats_score(resume_text, job_keywords=None):
    if not resume_text:
        return 0.0

    text = resume_text.lower()
    wc = len(text.split())
    resume_skills = set(s.lower() for s in extract_skills(resume_text))

    # ---- Skill Saturation (40%)
    if job_keywords:
        jd = set(k.lower() for k in job_keywords)
        ratio = len(resume_skills & jd) / max(1, len(jd))

        if ratio >= 0.6:
            skill_score = 1.0
        elif ratio >= 0.4:
            skill_score = 0.85
        elif ratio >= 0.25:
            skill_score = 0.7
        else:
            skill_score = ratio
    else:
        skill_score = min(1.0, len(resume_skills) / 8.0)

    # ---- Structure (20%)
    sections = ["experience", "education", "skills", "projects", "summary"]
    section_score = sum(1 for s in sections if s in text) / len(sections)

    # ---- Experience (15%)
    exp_list = extract_experience(resume_text)
    years = 0.0
    for e in exp_list:
        m = re.search(r"(\d+(?:\.\d+)?)", e)
        if m:
            years = max(years, float(m.group(1)))

    if years == 0:
        exp_score = 0.6
    elif years <= 2:
        exp_score = 0.7
    elif years <= 5:
        exp_score = 0.85
    else:
        exp_score = 1.0

    # ---- Parseability (15%)
    if wc < 80:
        parse_score = 0.3
    elif wc < 150:
        parse_score = 0.6
    elif wc < 300:
        parse_score = 0.85
    else:
        parse_score = 1.0

    # ---- Project Bonus
    project_terms = [
        "designed", "implemented", "optimized", "scalable",
        "distributed", "latency", "throughput",
        "docker", "kubernetes", "aws"
    ]
    hits = sum(1 for k in project_terms if k in text)
    project_bonus = 0.12 if hits >= 6 else 0.08 if hits >= 3 else 0.0

    # ---- Penalties
    penalty = 0.0
    if wc < 60:
        penalty += 0.1
    if len(resume_skills) > 40:
        penalty += 0.1

    final = (
        0.40 * skill_score +
        0.20 * section_score +
        0.15 * exp_score +
        0.15 * parse_score
    )

    final = final + project_bonus - min(0.2, penalty)
    return round(max(0.0, min(1.0, final)) * 100, 2)
