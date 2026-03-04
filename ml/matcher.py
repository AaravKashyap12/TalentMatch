"""
Core scoring and extraction engine for TalentMatch.
"""

import re
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ---------------------------------------------------------------------------
# SKILLS DATABASE  (expanded)
# ---------------------------------------------------------------------------

SKILLS_DB = [
    # Languages
    "python", "java", "c++", "c", "c#", "javascript", "typescript", "go",
    "rust", "swift", "kotlin", "php", "ruby", "scala", "r", "matlab",
    "perl", "bash", "shell", "powershell", "dart", "elixir", "haskell",
    "lua", "groovy", "assembly",

    # Web / Frontend
    "html", "css", "react", "angular", "vue", "svelte", "next.js", "nuxt",
    "gatsby", "remix", "tailwind", "tailwindcss", "bootstrap", "sass",
    "scss", "webpack", "vite", "babel", "jquery",

    # Backend / Frameworks
    "node.js", "express", "nestjs", "django", "flask", "fastapi",
    "spring boot", "spring", "rails", "laravel", "asp.net", "dotnet",
    "graphql", "rest api", "grpc", "websocket",

    # ML / AI / Data Science
    "machine learning", "deep learning", "data science", "nlp",
    "natural language processing", "computer vision", "reinforcement learning",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "scipy", "matplotlib", "seaborn", "xgboost", "lightgbm", "catboost",
    "hugging face", "transformers", "langchain", "openai", "llm",
    "generative ai", "rag", "embeddings", "mlflow", "airflow", "spark",
    "hadoop", "hive", "tableau", "power bi",

    # Cloud / DevOps / Infra
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "terraform", "ansible", "chef", "puppet", "jenkins", "github actions",
    "gitlab ci", "ci/cd", "linux", "unix", "nginx", "apache",
    "cloudformation", "pulumi", "helm", "istio", "prometheus", "grafana",
    "datadog", "elk", "elasticsearch",

    # Databases
    "sql", "nosql", "mongodb", "postgresql", "mysql", "sqlite", "redis",
    "cassandra", "dynamodb", "firebase", "supabase", "neo4j", "oracle",
    "snowflake", "bigquery", "dbt",

    # Messaging / Streaming
    "kafka", "rabbitmq", "celery", "sqs", "pubsub",

    # Version Control / Collaboration
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "agile", "scrum", "kanban",

    # CS Fundamentals
    "data structures", "algorithms", "system design", "oop",
    "object oriented", "design patterns", "microservices", "api design",
    "distributed systems",

    # Mobile
    "android", "ios", "react native", "flutter",

    # Security
    "cybersecurity", "penetration testing", "oauth", "jwt", "ssl", "tls",

    # Testing
    "unit testing", "integration testing", "pytest", "jest", "selenium",
    "cypress", "test driven development", "tdd",
]


def _normalize(text: str) -> str:
    """Normalize text for skill matching: lowercase, collapse dashes/dots to spaces."""
    return re.sub(r"[-./]", " ", text.lower())


def extract_skills(text: str) -> list:
    """
    Extract skills from text using the SKILLS_DB.
    """
    norm_text = _normalize(text)
    found = set()

    for skill in SKILLS_DB:
        norm_skill = _normalize(skill)
        if len(norm_skill.replace(" ", "")) <= 3:
            pattern = rf"(?:^|\s){re.escape(norm_skill)}(?:$|[\s,./])"
        else:
            pattern = rf"\b{re.escape(norm_skill)}\b"

        if re.search(pattern, norm_text):
            found.add(skill)

    return sorted(found)


# ---------------------------------------------------------------------------
# DATE PARSING
# ---------------------------------------------------------------------------

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_date(date_str: str):
    """
    Parse a date string into a datetime object.
    """
    date_str = date_str.strip().lower()
    if date_str in ("present", "current", "now", "till date", "till present"):
        return datetime.now()

    date_str = re.sub(r"[,.]", "", date_str)

    try:
        if re.fullmatch(r"\d{4}", date_str):
            return datetime(int(date_str), 1, 1)

        m = re.match(r"(\d{1,2})[/-](\d{4})", date_str)
        if m:
            return datetime(int(m.group(2)), int(m.group(1)), 1)

        parts = date_str.split()
        if len(parts) >= 2:
            month_key = parts[0][:4]
            month = MONTH_MAP.get(month_key) or MONTH_MAP.get(month_key[:3])
            year_str = parts[-1]
            if month and year_str.isdigit():
                return datetime(int(year_str), month, 1)
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# EXPERIENCE EXTRACTION
# ---------------------------------------------------------------------------

EXPERIENCE_HEADERS = [
    "work experience", "employment history", "professional experience",
    "work history", "career history", "professional background",
]
WEAK_EXPERIENCE_HEADERS = ["experience"]

STOP_HEADERS = [
    "education", "academic", "projects", "skills", "certifications",
    "achievements", "leadership", "activities", "interests", "summary",
    "coursework", "hobbies", "awards", "publications", "references",
    "volunteer", "extracurricular",
]

MONTHS_PATTERN = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)"
)

# Use hex escapes for dashes to avoid console encoding issues on Windows
DATE_RANGE_PATTERN = (
    rf"(\b{MONTHS_PATTERN}\.?\s*\d{{4}}|\b\d{{1,2}}[/-]\d{{4}}|\b\d{{4}})"
    r"\s*(?:-|\u2013|\u2014|to)\s*"
    rf"(present|current|now|till\s*date|till\s*present|\b{MONTHS_PATTERN}\.?\s*\d{{4}}|\b\d{{1,2}}[/-]\d{{4}}|\b\d{{4}})"
)


def _find_section(text_l: str, headers: list, strong=True) -> int | None:
    for h in headers:
        pattern = rf"(?:^|\n)\s*{re.escape(h)}[\s:.\-_]*(?:\n|$)"
        m = re.search(pattern, text_l)
        if not m and strong:
            m = re.search(rf"(?:^|\n)([^\n]{{1,50}}{re.escape(h)}[^\n]{{0,20}})(?:\n|$)", text_l)
            if m:
                line = m.group(1).strip()
                if len(line.split()) > 5:
                    m = None
        if m:
            return m.end()
    return None


ROLE_KEYWORDS = [
    "engineer", "developer", "intern", "analyst", "manager", "lead", "architect",
    "designer", "consultant", "specialist", "scientist", "researcher",
    "programmer", "technician", "associate", "officer", "administrator",
    "coordinator", "trainee", "founder", "co-founder", "startup", "cto", "ceo"
]

def extract_experience(text: str) -> list:
    """
    Extract total professional experience in years.
    """
    # Nuclear ASCII-fication to prevent Windows terminal encoding crashes during traceback/logging
    text_l = text.encode("ascii", "ignore").decode("ascii").lower()

    explicit = re.findall(
        r"(\d+)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+)?experience",
        text_l
    )
    if explicit:
        years = max(int(x) for x in explicit)
        return [f"{min(years, 40):.1f} Years"]

    start = _find_section(text_l, EXPERIENCE_HEADERS, strong=True)
    if start is None:
        start = _find_section(text_l, WEAK_EXPERIENCE_HEADERS, strong=False)

    if start is None:
        return ["0.0 Years"]

    end = len(text_l)
    for h in STOP_HEADERS:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|\n|$)", text_l[start:])
        if m:
            candidate_end = start + m.start()
            if candidate_end > start:
                end = min(end, candidate_end)
    
    work_section = text_l[start:end]

    # PRE-CLEANING: Actively remove non-work sections that might have bled through
    for h in ["education", "projects", "leadership", "achievements"]:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|\n|$)", work_section)
        if m:
            work_section = work_section[:m.start()]

    ranges = []
    for match in re.finditer(DATE_RANGE_PATTERN, work_section):
        s_str, e_str = match.groups()
        context_start = max(0, match.start() - 120)
        context_end = min(len(work_section), match.end() + 120)
        context = work_section[context_start:context_end]
        has_role = any(role in context for role in ROLE_KEYWORDS)
        
        if has_role:
            d1 = parse_date(s_str)
            d2 = parse_date(e_str)
            if d1 and d2 and d2 >= d1:
                ranges.append((d1, d2))

    if not ranges:
        return ["0.0 Years"]

    ranges.sort()
    merged = [ranges[0]]
    for s, e in ranges[1:]:
        last_s, last_e = merged[-1]
        if s <= last_e:
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))

    total_days = sum((e - s).days for s, e in merged)
    years = total_days / 365.25
    return [f"{min(years, 40):.1f} Years"]


# ---------------------------------------------------------------------------
# EDUCATION EXTRACTION
# ---------------------------------------------------------------------------

EDUCATION_HEADERS = [
    "education", "academic history", "educational background",
    "academics", "qualifications", "academic qualifications",
]

EDUCATION_STOP_HEADERS = [
    "experience", "work experience", "employment", "skills",
    "projects", "certifications", "achievements", "summary",
    "awards", "publications", "references",
]


def extract_education(text: str) -> str:
    """
    Detect highest degree from resume text.
    """
    for header in ["EDUCATION", "SKILLS", "EXPERIENCE", "PROJECTS", "SUMMARY", "AWARDS"]:
        text = re.sub(rf"([a-z\.,])({header})", r"\1\n\2", text)

    text_l = text.lower()
    text_l = re.sub(r"\be\s+d\s+u\s+c\s+a\s+t\s+i\s+o\s+n\b", "education", text_l)

    start = None
    for h in EDUCATION_HEADERS:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|\n|$)", text_l)
        if m:
            start = m.end()
            break

    if start is not None:
        end = len(text_l)
        for h in EDUCATION_STOP_HEADERS:
            m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|\n|$)", text_l[start:])
            if m:
                candidate_end = start + m.start()
                if candidate_end > start:
                    end = min(end, candidate_end)
        section = text_l[start:end]
    else:
        section = text_l

    if re.search(r"\b(ph\.?\s*d\.?|doctorate|doctor of philosophy|d\.phil)\b", section):
        return "PhD"
    if re.search(r"\b(master(?:s|\s+of|\s+'s)?|m\.?b\.?a\.?|m\.?s\.?c?\.?|m\.?tech|m\.?eng|m\.?e\.)\b", section):
        return "Master"
    if re.search(r"\b(bachelor(?:s|\s+of|\s+'s)?|b\.?s\.?c?\.?|b\.?tech|b\.?e\.?(?!\s+and)|b\.?eng|b\.?a\.?)\b", section):
        return "Bachelor"
    if re.search(r"\b(associate(?:\s+of|\s+degree)?|a\.s\.|a\.a\.)\b", section):
        return "Associate"

    return "None"


# ---------------------------------------------------------------------------
# TF-IDF SIMILARITY
# ---------------------------------------------------------------------------

def calculate_similarity(job_desc: str, resumes: list) -> list:
    if not resumes or not job_desc:
        return [0.0] * len(resumes)
    docs = [job_desc] + resumes
    tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    matrix = tfidf.fit_transform(docs)
    scores = cosine_similarity(matrix[0:1], matrix[1:])
    return scores[0].tolist()


# ---------------------------------------------------------------------------
# COMPONENT SCORING
# ---------------------------------------------------------------------------

def calculate_component_scores(
    job_desc_clean: str,
    resumes_clean: list,
    job_desc_raw: str,
    resumes_raw: list,
    weights: dict,
) -> list:
    similarity_clean = calculate_similarity(job_desc_clean, resumes_clean)
    similarity_raw = calculate_similarity(job_desc_raw, resumes_raw)
    jd_skills = set(extract_skills(job_desc_raw))
    results = []

    for i, raw in enumerate(resumes_raw):
        resume_skills = set(extract_skills(raw))
        if jd_skills:
            skills_score = len(jd_skills & resume_skills) / max(1, len(jd_skills))
        else:
            skills_score = min(1.0, len(resume_skills) / 10.0)

        exp_str = extract_experience(raw)[0]
        years = float(re.search(r"\d+(\.\d+)?", exp_str).group())
        exp_score = min(1.0, years / 15.0)

        degree = extract_education(raw)
        edu_map = {"PhD": 1.0, "Master": 0.8, "Bachelor": 0.6, "Associate": 0.4, "None": 0.1}
        edu_score = edu_map.get(degree, 0.1)

        relevance_score = (similarity_clean[i] + similarity_raw[i]) / 2.0
        raw_score = (
            weights["skills"] * skills_score
            + weights["experience"] * exp_score
            + weights["education"] * edu_score
            + weights["relevance"] * relevance_score
        )
        total_weight = sum(weights.values()) or 1.0
        final = raw_score / total_weight

        results.append({
            "final_score": round(final * 100, 2),
            "skills_score": round(skills_score * 100, 1),
            "exp_score": round(exp_score * 100, 1),
            "edu_score": round(edu_score * 100, 1),
            "relevance_score": round(relevance_score * 100, 1),
            "degree": degree,
            "years_experience": round(years, 1),
        })

    return results


# ---------------------------------------------------------------------------
# ATS SCORE
# ---------------------------------------------------------------------------

def calculate_ats_score(resume_raw: str, job_keywords: set = None) -> float:
    text = resume_raw.encode("ascii", "ignore").decode("ascii").lower()
    wc = len(text.split())
    resume_skills = set(extract_skills(resume_raw))
    skill_score = min(1.0, len(resume_skills) / 10.0)
    sections = ["experience", "education", "skills", "projects", "summary", "certifications"]
    section_score = sum(1 for s in sections if s in text) / len(sections)

    kw_score = 0.0
    if job_keywords:
        overlap = len(resume_skills & job_keywords)
        kw_score = min(1.0, overlap / max(1, len(job_keywords)))

    parse_score = 0.3 if wc < 80 else 0.6 if wc < 200 else 0.85 if wc < 400 else 1.0
    final = (0.40 * skill_score + 0.25 * section_score + 0.20 * kw_score + 0.15 * parse_score)
    return round(max(0.0, min(1.0, final)) * 100, 2)
