"""
Core scoring and extraction engine for TalentMatch.

Memory-optimised edition for Render free tier (512 MB RAM):
- sentence-transformers / PyTorch removed (~400-600 MB saved).
- TF-IDF cosine similarity used as the sole relevance engine (~2 MB).
- get_embedder() retained as a no-op stub so existing call-sites don't break.
- All other scoring logic (skills, experience, education, ATS) unchanged.
"""

import re
import logging
from datetime import datetime
import threading
from typing import List, Set, Dict, Any, Tuple, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# EMBEDDER STUB — kept for API compatibility; always returns "tfidf"
# sentence-transformers removed to stay within Render free-tier 512 MB RAM.
# ---------------------------------------------------------------------------

_embedder = "tfidf"   # module-level so /health can inspect it
_embedder_lock = threading.Lock()


def get_embedder():
    """Returns 'tfidf'. sentence-transformers removed for memory reasons."""
    return _embedder


# ---------------------------------------------------------------------------
# SKILLS — hybrid: spaCy NER + curated seed list for precision
# ---------------------------------------------------------------------------

SKILLS_SEED = {
    # Languages
    "python","java","c++","c#","javascript","typescript","go","rust","swift",
    "kotlin","php","ruby","scala","r","matlab","perl","bash","shell","dart",
    "elixir","haskell","lua","groovy","assembly","sql","html","css",
    # Web
    "react","angular","vue","svelte","next.js","nuxt","gatsby","remix",
    "tailwind","tailwindcss","bootstrap","sass","scss","webpack","vite","jquery",
    # Backend
    "node.js","express","nestjs","django","flask","fastapi","spring boot",
    "spring","rails","laravel","asp.net","graphql","grpc","websocket","trpc",
    # Databases
    "mongodb","postgresql","mysql","sqlite","redis","cassandra","dynamodb",
    "firebase","supabase","neo4j","oracle","snowflake","bigquery","dbt",
    "prisma","typeorm","sequelize","mongoose","drizzle","sqlalchemy",
    # Cloud / DevOps
    "aws","azure","gcp","docker","kubernetes","k8s","terraform","ansible",
    "jenkins","github actions","gitlab ci","ci/cd","linux","nginx","apache",
    "cloudformation","helm","prometheus","grafana","datadog","elasticsearch",
    "kafka","rabbitmq","celery","sqs","pubsub","vercel","netlify","render",
    "neon","upstash","planetscale",
    # ML / AI
    "tensorflow","pytorch","keras","scikit-learn","pandas","numpy","scipy",
    "matplotlib","seaborn","xgboost","lightgbm","hugging face","huggingface",
    "transformers","langchain","openai","llm","rag","embeddings","mlflow",
    "airflow","spark","hadoop","tableau","power bi","streamlit","jupyter",
    "groq","ollama","pinecone","weaviate","qdrant","chroma",
    # Mobile
    "android","ios","react native","flutter",
    # Testing
    "pytest","jest","selenium","cypress","playwright","vitest",
    # CS fundamentals
    "data structures","algorithms","system design","oop","object oriented",
    "design patterns","microservices","distributed systems","api design",
    # Security
    "oauth","jwt","ssl","tls",
    # Misc modern
    "socket.io","zod","zustand","redux","stripe","razorpay",
    "cashfree","twilio","sendgrid","resend","clerk","auth0","nextauth",
    "git","github","gitlab","jira","agile","scrum","kanban",
}

SKILL_ALIASES = {
    "k8s": "kubernetes",
    "reactjs": "react",
    "react.js": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "nextjs": "next.js",
    "next.js": "next.js",
    "vuejs": "vue",
    "vue.js": "vue",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "golang": "go",
    "t-sql": "sql",
}


def _normalize(text: str) -> str:
    return re.sub(r"[-./]", " ", text.lower())


_NER_BLOCKLIST = {
    "india","usa","us","uk","canada","australia","germany","france","singapore",
    "london","new york","san francisco","seattle","austin","chicago","boston",
    "bangalore","hyderabad","mumbai","delhi","chennai","pune","new delhi",
    "california","texas","washington","new york city","nyc","sf","la",
    "university","college","institute","school","academy","foundation",
    "department","division","group","team","lab","laboratory","center","centre",
    "company","corporation","pvt","ltd","inc","llc","co","corp",
    "summary","experience","education","skills","projects","achievements",
    "certifications","references","work","employment","career","profile",
    "january","february","march","april","may","june","july","august",
    "september","october","november","december",
    "present","current","remote","full time","part time","contract","freelance",
    "bachelor","bachelors","bachelor's","bs","b.s","bsc","b.sc",
    "master","masters","master's","ms","m.s","msc","m.sc","mba","m.b.a",
    "phd","ph.d","doctorate","doctoral","associate","diploma","degree",
    "undergraduate","postgraduate","graduate","alumni","graduate student",
    "computer science","information technology","information systems",
    "electrical engineering","mechanical engineering","civil engineering",
    "mathematics","statistics","physics","biology","chemistry",
    "software engineer","software developer","software development",
    "senior software engineer","junior software engineer",
    "full stack developer","backend developer","frontend developer",
    "data scientist","data analyst","data engineer","ml engineer",
    "product manager","project manager","engineering manager",
    "devops engineer","cloud engineer","security engineer",
    "web developer","mobile developer","ios developer","android developer",
    "intern","internship","trainee","fresher","entry level",
    "required","preferred","must have","nice to have","excellent",
    "strong","proficient","familiarity","knowledge","understanding",
    "experience with","years of experience","minimum","plus","bonus",
    "ability","communication","problem solving","team player","collaborative",
    "analytical","detail oriented","fast learner","self motivated",
    "opportunity","position","role","responsibilities","requirements",
    "qualifications","candidate","applicant","hire","hiring",
}


def extract_skills(text: str) -> list:
    found = set()
    norm = _normalize(text)

    for skill in SKILLS_SEED:
        ns = _normalize(skill)
        if len(ns.replace(" ", "")) <= 3:
            pat = rf"(?:^|\s){re.escape(ns)}(?:$|[\s,./])"
        else:
            pat = rf"\b{re.escape(ns)}\b"
        if re.search(pat, norm):
            found.add(skill)

    try:
        from ml.nlp_utils import get_nlp
        nlp = get_nlp()
        doc = nlp(text[:8000])
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT"):
                val = ent.text.strip()
                val_lower = val.lower()
                if 1 <= len(val.split()) <= 3 and len(val) <= 30:
                    if set(val_lower.split()) & _NER_BLOCKLIST:
                        continue
                    if not re.search(
                        r"[,;]|\binc\b|\bltd\b|\bllc\b|\buniversity\b|\binstitute\b"
                        r"|\bcollege\b|\bschool\b|\bpvt\b|\bcorp\b",
                        val_lower
                    ):
                        found.add(val_lower)
    except Exception as e:
        logger.debug("NER skill extraction failed: %s", e)

    final_skills = set()
    for s in found:
        final_skills.add(SKILL_ALIASES.get(s, s))

    return sorted(final_skills)


# ---------------------------------------------------------------------------
# DATE PARSING
# ---------------------------------------------------------------------------

MONTH_MAP = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
    "jul":7,"aug":8,"sep":9,"sept":9,"oct":10,"nov":11,"dec":12,
}


def parse_date(date_str: str):
    date_str = date_str.strip().lower()
    if date_str in ("present","current","now","till date","till present","ongoing","today"):
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
            if month and year_str.isdigit() and 1990 <= int(year_str) <= 2030:
                return datetime(int(year_str), month, 1)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# EXPERIENCE EXTRACTION
# ---------------------------------------------------------------------------

EXPERIENCE_HEADERS = [
    "work experience","employment history","professional experience",
    "work history","career history","professional background","experience",
]

STOP_HEADERS = [
    "education","academic","projects","skills","certifications",
    "achievements","leadership","activities","interests","summary",
    "coursework","hobbies","awards","publications","references",
    "volunteer","extracurricular",
]

MONTHS_PATTERN = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?"
    r"|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)

DATE_RANGE_PATTERN = (
    rf"(\b{MONTHS_PATTERN}\.?\s*\d{{4}}|\b\d{{1,2}}[/-]\d{{4}}|\b\d{{4}})"
    r"\s*(?:-|\u2013|\u2014|to|–)\s*"
    rf"(present|current|now|ongoing|till\s*date|till\s*present|\b{MONTHS_PATTERN}\.?\s*\d{{4}}|\b\d{{1,2}}[/-]\d{{4}}|\b\d{{4}})"
)

ROLE_KEYWORDS = [
    "engineer","developer","intern","analyst","manager","lead","architect",
    "designer","consultant","specialist","scientist","researcher","programmer",
    "associate","officer","administrator","coordinator","trainee","founder",
    "co-founder","cto","ceo","sde","swe","contractor","freelance",
]


def _find_section(text_l: str, headers: list) -> int | None:
    for h in headers:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}[\s:.\-_]*(?:\n|$)", text_l)
        if m:
            return m.end()
    return None


def extract_experience(text: str) -> list:
    text_l = text.encode("ascii", "ignore").decode("ascii").lower()

    explicit = re.findall(
        r"(\d+\.?\d*)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+|relevant\s+)?experience",
        text_l
    )
    if explicit:
        years = max(float(x) for x in explicit)
        return [f"{min(years, 40):.1f} Years"]

    start = _find_section(text_l, EXPERIENCE_HEADERS)
    if start is None:
        return ["0.0 Years"]

    end = len(text_l)
    for h in STOP_HEADERS:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|$)", text_l[start:])
        if m:
            cand = start + m.start()
            if cand > start:
                end = min(end, cand)

    work_section = text_l[start:end]

    for h in ["education","projects","leadership","achievements"]:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|$)", work_section)
        if m:
            work_section = work_section[:m.start()]

    ranges = []
    for match in re.finditer(DATE_RANGE_PATTERN, work_section, re.IGNORECASE):
        s_str, e_str = match.groups()
        ctx = work_section[max(0, match.start()-150):match.end()+150]
        has_role = any(re.search(rf"\b{re.escape(role)}\b", ctx) for role in ROLE_KEYWORDS)
        if has_role:
            d1 = parse_date(s_str)
            d2 = parse_date(e_str)
            if d1 and d2 and d2 >= d1:
                span_years = (d2 - d1).days / 365.25
                if span_years <= 6:
                    ranges.append((d1, d2))

    if not ranges:
        return ["0.0 Years"]

    ranges.sort()
    merged = [ranges[0]]
    for s, e in ranges[1:]:
        ls, le = merged[-1]
        if s <= le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))

    total_days = sum((e - s).days for s, e in merged)
    years = total_days / 365.25
    return [f"{min(years, 40):.1f} Years"]


# ---------------------------------------------------------------------------
# EDUCATION EXTRACTION
# ---------------------------------------------------------------------------

EDUCATION_HEADERS = [
    "education","academic history","educational background",
    "academics","qualifications","academic qualifications",
]

EDUCATION_STOP_HEADERS = [
    "experience","work experience","employment","skills","projects",
    "certifications","achievements","summary","awards","publications","references",
]


def extract_education(text: str) -> str:
    for header in ["EDUCATION","SKILLS","EXPERIENCE","PROJECTS","SUMMARY","AWARDS"]:
        text = re.sub(rf"([a-z\.,])({header})", r"\1\n\2", text)

    text_l = text.lower()
    text_l = re.sub(r"\be\s+d\s+u\s+c\s+a\s+t\s+i\s+o\s+n\b", "education", text_l)

    start = None
    for h in EDUCATION_HEADERS:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|$)", text_l)
        if m:
            start = m.end()
            break

    section = text_l
    if start is not None:
        end = len(text_l)
        for h in EDUCATION_STOP_HEADERS:
            m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|$)", text_l[start:])
            if m:
                cand = start + m.start()
                if cand > start:
                    end = min(end, cand)
        section = text_l[start:end]

    if re.search(r"\b(ph\.?\s*d\.?|doctorate|doctor of philosophy|d\.phil)\b", section):
        return "PhD"
    if re.search(r"\b(master(?:s|'s)?|master\s+of|m\.b\.a\.?|m\.sc?\.?|m\.tech|m\.eng|mtech|meng)\b", section):
        return "Master"
    if re.search(
        r"\b(bachelor(?:s|\s+of|\s+'s)?|b\.s\.c?\.?|b\.tech|b\.e\.|b\.eng\.|b\.a\.)(?!\w)",
        section
    ):
        return "Bachelor"
    if re.search(r"\b(associate(?:\s+of|\s+degree)?|a\.s\.|a\.a\.)\b", section):
        return "Associate"
    return "None"


# ---------------------------------------------------------------------------
# SEMANTIC SIMILARITY — TF-IDF cosine similarity
# sentence-transformers removed: PyTorch alone uses ~400 MB on Render free tier.
# TF-IDF with bigrams + sublinear_tf is a solid lightweight alternative.
# ---------------------------------------------------------------------------

def calculate_similarity(job_desc: str, resumes: list) -> list:
    """
    Compute TF-IDF cosine similarity between the job description and each resume.
    ~2 MB footprint, no external model download, instant startup.
    """
    if not resumes or not job_desc:
        return [0.0] * len(resumes)

    from sklearn.feature_extraction.text import TfidfVectorizer
    docs = [job_desc] + resumes
    tfidf = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
        max_features=20_000,   # cap vocabulary to keep memory bounded
    )
    matrix = tfidf.fit_transform(docs)
    scores = cosine_similarity(matrix[0:1], matrix[1:])
    return scores[0].tolist()


# ---------------------------------------------------------------------------
# REAL ATS SCORING
# ---------------------------------------------------------------------------

def calculate_ats_score(resume_raw: str, job_keywords: set = None) -> float:
    text = resume_raw
    text_l = text.lower()
    words = text_l.split()
    wc = len(words)
    score = 0.0
    max_score = 0.0

    def check(weight, condition):
        nonlocal score, max_score
        max_score += weight
        if condition:
            score += weight

    email_compact = re.sub(r"\s+", "", text)
    check(5, bool(re.search(r"[\w.+-]+@[\w-]+\.\w+", email_compact)))
    check(5, bool(re.search(r"(\+?\d[\d\s\-().]{7,}\d)", text)))

    sections = {
        "experience": ["experience", "employment", "work history"],
        "education":  ["education", "academic"],
        "skills":     ["skills", "technical skills", "technologies"],
        "projects":   ["projects", "portfolio"],
        "summary":    ["summary", "objective", "profile", "about"],
    }
    for sec, keywords in sections.items():
        has = any(re.search(rf"(?:^|\n)\s*{kw}", text_l) for kw in keywords)
        check(6, has)

    garble_ratio = len(re.findall(r"\s{3,}", text)) / max(wc, 1)
    check(5, garble_ratio < 0.5)
    spaced_chars = len(re.findall(r"(?<=[a-zA-Z]) (?=[a-zA-Z])", text[:500]))
    check(5, spaced_chars < 20)
    non_ascii = sum(1 for c in text if ord(c) > 127) / max(len(text), 1)
    check(5, non_ascii < 0.05)

    check(5, wc >= 300)
    check(5, wc <= 1200)

    std_dates = re.findall(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}\b",
        text_l
    )
    bad_dates = re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", text_l)
    check(10, len(std_dates) >= len(bad_dates))

    if job_keywords:
        resume_skills = set(extract_skills(resume_raw))
        overlap = len(resume_skills & job_keywords)
        kw_ratio = overlap / max(len(job_keywords), 1)
        max_score += 25
        score += round(min(25.0, kw_ratio * 25.0), 2)

    raw = (score / max_score) * 100 if max_score else 0
    return round(min(100, max(0, raw)), 2)


# ---------------------------------------------------------------------------
# COMPONENT SCORING
# ---------------------------------------------------------------------------

def calculate_component_scores(
    job_desc_clean: str,
    resumes_clean: list,
    job_desc_raw: str,
    resumes_raw: list,
    weights: dict,
    jd_skills: set | None = None,
    experience_cap_years: float = 15.0,
) -> list:
    similarity_scores = calculate_similarity(job_desc_raw, resumes_raw)

    if jd_skills is None:
        jd_skills = set(extract_skills(job_desc_raw))

    # TF-IDF scores are typically 0.0–0.6; rescale to 0–1
    LOWER_BOUND = 0.0
    UPPER_BOUND = 0.6

    results = []
    for i, raw in enumerate(resumes_raw):
        resume_skills = set(extract_skills(raw))

        if jd_skills:
            skills_score = len(jd_skills & resume_skills) / max(1, len(jd_skills))
        else:
            skills_score = 0.0

        exp_str = extract_experience(raw)[0]
        years = float(re.search(r"\d+(\.\d+)?", exp_str).group())
        exp_score = min(1.0, years / experience_cap_years)

        degree = extract_education(raw)
        edu_map = {"PhD": 1.0, "Master": 0.8, "Bachelor": 0.6, "Associate": 0.4}
        edu_score = edu_map.get(degree, 0.3)

        raw_sim = float(similarity_scores[i])
        relevance_score = max(0.0, min(1.0, (raw_sim - LOWER_BOUND) / (UPPER_BOUND - LOWER_BOUND)))

        raw_score = (
            weights["skills"]     * skills_score
            + weights["experience"] * exp_score
            + weights["education"]  * edu_score
            + weights["relevance"]  * relevance_score
        )
        total_weight = sum(weights.values()) or 1.0
        final = raw_score / total_weight

        results.append({
            "final_score":      round(final * 100, 2),
            "skills_score":     round(skills_score * 100, 1),
            "exp_score":        round(exp_score * 100, 1),
            "edu_score":        round(edu_score * 100, 1),
            "relevance_score":  round(relevance_score * 100, 1),
            "degree":           degree,
            "years_experience": round(years, 1),
            "experience_str":   exp_str,
            "resume_skills":    resume_skills,
        })

    return results


# ---------------------------------------------------------------------------
# STRUCTURED JD SCORING
# ---------------------------------------------------------------------------

DEGREE_ORDER = {"None": 0, "Associate": 1, "Bachelor": 2, "Master": 3, "PhD": 4}


def calculate_component_scores_structured(
    job_desc_clean: str,
    resumes_clean: List[str],
    job_desc_raw: str,
    resumes_raw: List[str],
    weights: Dict[str, float],
    jd_skills: Optional[Set[str]] = None,
    preferred_skills: Optional[Set[str]] = None,
    experience_cap_years: float = 15.0,
    min_years_experience: Optional[float] = None,
    required_degree: Optional[str] = None,
) -> List[Dict[str, Any]]:
    similarity_scores = calculate_similarity(job_desc_raw, resumes_raw)

    if jd_skills is None:
        jd_skills = set(extract_skills(job_desc_raw))
    if preferred_skills is None:
        preferred_skills = set()

    # TF-IDF similarity bounds (empirical for resume/JD pairs)
    LOWER_BOUND = 0.0
    UPPER_BOUND = 0.6

    results = []
    for i, raw in enumerate(resumes_raw):
        resume_skills = set(extract_skills(raw))

        if jd_skills or preferred_skills:
            req_ratio  = len(jd_skills & resume_skills) / max(1, len(jd_skills)) if jd_skills else 0.0
            pref_ratio = len(preferred_skills & resume_skills) / max(1, len(preferred_skills)) if preferred_skills else 0.0
            skills_score = (0.8 * req_ratio) + (0.2 * pref_ratio)
        else:
            skills_score = 0.0

        exp_str = extract_experience(raw)[0]
        years = float(re.search(r"\d+(\.\d+)?", exp_str).group())
        exp_score = min(1.0, years / experience_cap_years)

        meets_min_exp = None
        if min_years_experience is not None:
            meets_min_exp = years >= min_years_experience
            if not meets_min_exp:
                exp_score = min(exp_score, 0.5)

        degree = extract_education(raw)
        edu_map = {"PhD": 1.0, "Master": 0.8, "Bachelor": 0.6, "Associate": 0.4}
        edu_score = edu_map.get(degree, 0.3)

        meets_degree_req = None
        if required_degree and required_degree != "None":
            candidate_rank = DEGREE_ORDER.get(degree, 0)
            required_rank  = DEGREE_ORDER.get(required_degree, 0)
            meets_degree_req = candidate_rank >= required_rank
            if not meets_degree_req:
                edu_score = edu_score * 0.5

        raw_sim = float(similarity_scores[i])
        relevance_score = max(0.0, min(1.0, (raw_sim - LOWER_BOUND) / (UPPER_BOUND - LOWER_BOUND)))

        raw_score = (
            weights["skills"]     * skills_score
            + weights["experience"] * exp_score
            + weights["education"]  * edu_score
            + weights["relevance"]  * relevance_score
        )
        total_weight = sum(weights.values()) or 1.0
        final = raw_score / total_weight

        results.append({
            "final_score":             round(final * 100, 2),
            "skills_score":            round(skills_score * 100, 1),
            "exp_score":               round(exp_score * 100, 1),
            "edu_score":               round(edu_score * 100, 1),
            "relevance_score":         round(relevance_score * 100, 1),
            "degree":                  degree,
            "years_experience":        round(years, 1),
            "experience_str":          exp_str,
            "resume_skills":           resume_skills,
            "missing_required_skills": sorted(jd_skills - resume_skills),
            "meets_min_experience":    meets_min_exp,
            "meets_degree_req":        meets_degree_req,
        })

    return results
