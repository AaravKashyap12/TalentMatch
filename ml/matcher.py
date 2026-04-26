"""
Core scoring and extraction engine for TalentMatch.

Memory-optimised edition for small production containers:
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
from pipeline.skills import (
    match_skills,
    extract_jd_skills,
    extract_jd_skill_tiers,
    normalize_skill,
    SKILLS_SEED,
    SKILL_ALIASES,
)

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# EMBEDDER STUB — kept for API compatibility; always returns "tfidf"
# sentence-transformers removed to stay within small-container memory budgets.
# ---------------------------------------------------------------------------

_embedder = "tfidf"   # module-level so /health can inspect it
_embedder_lock = threading.Lock()


def get_embedder():
    """Returns 'tfidf'. sentence-transformers removed for memory reasons."""
    return _embedder


# ---------------------------------------------------------------------------
# SKILLS — hybrid: spaCy NER + curated seed list for precision
# SKILLS_SEED and SKILL_ALIASES now imported from pipeline.skills to avoid
# circular imports when extract_jd_skills is called.
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Normalise text for skill matching.

    Handles several classes of PDF-extraction artifacts that break word-boundary
    matching for compound skill names like "JavaScript" and "TypeScript":

      • Zero-width spaces / non-joiners (U+200B–200F) inserted by pypdf
      • Soft hyphens (U+00AD) used by some PDF generators
      • Word joiners and BOM characters
      • En/em dashes WITHIN a word (e.g. "Java–Script" → "JavaScript")
      • Line-break hyphens (e.g. "Java-⏎Script" → "JavaScript")
    """
    # 1. Remove invisible zero-width / control characters
    text = re.sub(r"[\u00ad\u200b-\u200f\u2028\u2029\u2060\ufeff]", "", text)
    # 2. Typographic dashes between letters → join (no space), e.g. "Java–Script" → "JavaScript"
    text = re.sub(r"(?<=[A-Za-z])[\u2010-\u2015\u2212\u2013\u2014](?=[A-Za-z])", "", text)
    # 3. Remaining typographic dashes → regular hyphen (so "Node–js" → "Node-js" → "Node js")
    text = re.sub(r"[\u2010-\u2015\u2212\u2013\u2014]", "-", text)
    # 4. Rejoin words hyphenated across a line break ("Java-\nScript" → "JavaScript")
    text = re.sub(r"-\n\s*", "", text)
    # 5. Standard normalisation: hyphens, dots, slashes → space, then lowercase
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
    "software","engineer","backend","frontend","fullstack","full-stack",
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
                    if val_lower in _NER_BLOCKLIST or set(val_lower.split()) & _NER_BLOCKLIST:
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

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
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
    text_l = text.lower()
    text_l = re.sub(r"[\u2010-\u2015\u2212]", "-", text_l)

    explicit = re.findall(
        r"(\d+\.?\d*)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+|relevant\s+|production\s+|industry\s+|commercial\s+)?experience",
        text_l
    )
    if explicit:
        years = max(float(x) for x in explicit)
        return [f"{min(years, 40):.1f} Years"]

    explicit_words = re.findall(
        r"\b(" + "|".join(NUMBER_WORDS) + r")\b\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+|relevant\s+|production\s+|industry\s+|commercial\s+)?experience",
        text_l
    )
    if explicit_words:
        years = max(NUMBER_WORDS[x] for x in explicit_words)
        return [f"{min(float(years), 40):.1f} Years"]

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
    if re.search(r"(?<!\w)(master(?:s|'s)?|master\s+of|mba|m\.b\.a\.?|m\.?sc\.?|m\.tech|m\.eng|mtech|meng)(?!\w)", section):
        return "Master"
    if re.search(
        r"(?<!\w)(bachelor(?:s|\s+of|\s+'s)?|b\.?sc\.?|b\.tech|b\.e\.|b\.eng\.|b\.a\.)(?!\w)",
        section
    ):
        return "Bachelor"
    if re.search(r"\b(associate(?:\s+of|\s+degree)?|a\.s\.|a\.a\.)\b", section):
        return "Associate"
    return "None"


# ---------------------------------------------------------------------------
# SEMANTIC SIMILARITY — TF-IDF cosine similarity
# sentence-transformers removed: PyTorch alone uses ~400 MB.
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

    # 🔥 FIX: use structured JD skills
    if jd_skills is None:
        jd_skills = set(extract_jd_skills(job_desc_raw))

    LOWER_BOUND = 0.0
    UPPER_BOUND = 0.6

    results = []
    for i, raw in enumerate(resumes_raw):
        resume_skills = set(extract_skills(raw))

        # 🔥 NEW SKILL MATCHING
        if jd_skills:
            skill_result = match_skills(list(resume_skills), list(jd_skills))

            matched = skill_result["matched_skills"]
            inferred = skill_result["inferred_skills"]
            weights_inf = skill_result["inference_weights"]

            score_val = len(matched)

            for _, w in weights_inf.items():
                score_val += w

            skills_score = score_val / max(1, len(jd_skills))
        else:
            skills_score = 0.0
            skill_result = {
                "missing_skills": [],
                "inferred_skills": []
            }

        # EXPERIENCE
        exp_str = extract_experience(raw)[0]
        years = float(re.search(r"\d+(\.\d+)?", exp_str).group())
        exp_score = min(1.0, years / experience_cap_years)

        # EDUCATION
        degree = extract_education(raw)
        edu_map = {"PhD": 1.0, "Master": 0.8, "Bachelor": 0.6, "Associate": 0.4}
        edu_score = edu_map.get(degree, 0.3)

        # RELEVANCE
        raw_sim = float(similarity_scores[i])
        relevance_score = max(0.0, min(1.0, (raw_sim - LOWER_BOUND) / (UPPER_BOUND - LOWER_BOUND)))
        skill_context_score = (0.75 * req_ratio) + (0.25 * pref_ratio)
        relevance_score = max(relevance_score, max(0.0, min(1.0, skill_context_score - 0.05)))
        skill_context_score = (0.75 * req_ratio) + (0.25 * pref_ratio)
        relevance_score = max(relevance_score, max(0.0, min(1.0, skill_context_score - 0.05)))

        # FINAL SCORE
        raw_score = (
            weights["skills"] * skills_score
            + weights["experience"] * exp_score
            + weights["education"] * edu_score
            + weights["relevance"] * relevance_score
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

            # 🔥 NEW OUTPUT
            "missing_required_skills": skill_result["missing_skills"],
            "matched_skills": sorted(set(skill_result["matched_skills"]) | set(skill_result["inferred_skills"])),
            "matched_preferred_skills": sorted(set(preferred_result["matched_skills"]) | set(preferred_result["inferred_skills"])),
            "inferred_skills": sorted(set(skill_result["inferred_skills"]) | set(preferred_result["inferred_skills"])),
        })

    return results


# ---------------------------------------------------------------------------
# STRUCTURED JD SCORING
# ---------------------------------------------------------------------------

DEGREE_ORDER = {"None": 0, "Associate": 1, "Bachelor": 2, "Master": 3, "PhD": 4}


BACKEND_STACK_SIGNALS = {
    "python": {
        "languages": {"python"},
        "frameworks": {"fastapi", "django", "flask"},
        "pattern": r"\b(python|fastapi|django|flask|sqlalchemy|pandas|numpy)\b",
    },
    "node.js": {
        "languages": {"javascript", "typescript", "node.js"},
        "frameworks": {"express", "nestjs", "next.js"},
        "pattern": r"\b(node\.?js|express|nestjs|javascript|typescript|next\.?js)\b",
    },
    "java": {
        "languages": {"java"},
        "frameworks": {"spring", "spring boot"},
        "pattern": r"\b(java|spring(?:\s+boot)?)\b",
    },
    "go": {
        "languages": {"go"},
        "frameworks": set(),
        "pattern": r"\b(go|golang)\b",
    },
}


def _confidence_credit(weight: float) -> float:
    if weight >= 0.95:
        return weight
    if weight >= 0.8:
        return weight * 0.9
    if weight >= 0.6:
        return weight * 0.75
    return weight * 0.55


def _primary_backend_language(text: str, skills: Set[str]) -> str | None:
    text_l = text.lower()
    scores: dict[str, float] = {}
    for language, cfg in BACKEND_STACK_SIGNALS.items():
        score = len(re.findall(cfg["pattern"], text_l))
        score += 3 * len(skills & cfg["languages"])
        score += 2 * len(skills & cfg["frameworks"])
        if score:
            scores[language] = float(score)
    if not scores:
        return None
    best, best_score = max(scores.items(), key=lambda item: item[1])
    return best if best_score >= 2 else None


ROLE_SIGNALS = {
    "backend": {
        "python", "fastapi", "django", "flask", "node.js", "express", "nestjs",
        "java", "spring", "spring boot", "go", "sql", "postgresql", "mongodb",
        "redis", "kafka", "rest api", "backend framework", "microservices",
        "distributed systems",
    },
    "ml": {
        "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
        "xgboost", "lightgbm", "mlflow", "jupyter", "machine learning",
        "artificial intelligence", "data scientist",
    },
    "frontend": {
        "react", "next.js", "vue", "angular", "svelte", "javascript",
        "typescript", "html", "css", "tailwind", "redux",
    },
    "devops": {
        "docker", "kubernetes", "terraform", "ansible", "jenkins",
        "github actions", "gitlab ci", "ci/cd", "aws", "gcp", "azure",
        "prometheus", "grafana", "nginx",
    },
}


def _role_family(text: str, skills: Set[str]) -> str | None:
    text_l = text.lower()
    scores = {role: len(skills & signals) for role, signals in ROLE_SIGNALS.items()}
    if re.search(r"\bbackend|api|microservice|server-side|server side\b", text_l):
        scores["backend"] += 4
    if re.search(r"\bmachine learning|deep learning|model|tensorflow|pytorch|data scientist\b", text_l):
        scores["ml"] += 4
    if re.search(r"\bfrontend|front-end|react|ui\b", text_l):
        scores["frontend"] += 4
    if re.search(r"\bdevops|infrastructure|kubernetes|terraform|ci/cd\b", text_l):
        scores["devops"] += 3

    role, score = max(scores.items(), key=lambda item: item[1])
    return role if score >= 2 else None


def _role_alignment(jd_role: str | None, resume_role: str | None) -> float:
    if not jd_role or not resume_role:
        return 0.65
    if jd_role == resume_role:
        return 1.0
    adjacent = {("backend", "devops"), ("devops", "backend"), ("backend", "frontend"), ("frontend", "backend")}
    if (jd_role, resume_role) in adjacent:
        return 0.7
    return 0.35


def _evidence_quality(text: str, skills: Set[str]) -> dict[str, Any]:
    text_l = text.lower()
    has_project = bool(re.search(r"(?m)^\s*(projects?|portfolio|experience|work experience|employment)\b", text_l))
    has_skills_only_section = bool(re.search(r"(?m)^\s*skills?\b", text_l)) and not has_project
    action_hits = len(re.findall(
        r"\b(built|designed|implemented|deployed|optimized|scaled|improved|reduced|increased|maintained|developed)\b",
        text_l,
    ))
    metric_hits = len(re.findall(
        r"(\b\d+(?:\.\d+)?\s*(?:%|ms|s|sec|seconds|k|m|rps|qps|req/s|requests|users|x)\b|~\s*\d+|latency|throughput)",
        text_l,
    ))
    skill_density = len(skills) / max(len(re.findall(r"\w+", text_l)), 1)
    score = 0.25
    if has_project:
        score += 0.3
    score += min(0.25, action_hits * 0.04)
    score += min(0.2, metric_hits * 0.05)
    skill_only_risk = len(skills) >= 15 and has_skills_only_section and action_hits < 3
    if len(skills) >= 8 and skill_density > 0.25 and action_hits < 2 and not has_project:
        skill_only_risk = True
    return {
        "score": max(0.0, min(1.0, score)),
        "has_metrics": metric_hits > 0,
        "metric_hits": metric_hits,
        "has_project_evidence": has_project or action_hits >= 3,
        "skill_only_risk": skill_only_risk,
    }


def _hiring_recommendation(score: float) -> str:
    if score >= 85:
        return "Strong Hire"
    if score >= 70:
        return "Hire"
    if score >= 55:
        return "Consider"
    return "Reject"


def _confidence_level(*, inferred_count: int, explicit_count: int, evidence_score: float, skill_only_risk: bool) -> str:
    total = inferred_count + explicit_count
    inferred_ratio = inferred_count / max(total, 1)
    if skill_only_risk:
        return "Low"
    if evidence_score >= 0.85 and inferred_ratio <= 0.65:
        return "High"
    if evidence_score >= 0.75 and inferred_ratio <= 0.45:
        return "High"
    if evidence_score >= 0.5 and inferred_ratio <= 0.65:
        return "Medium"
    return "Low"


def _explanation_for_candidate(
    *,
    jd_primary: str | None,
    resume_primary: str | None,
    stack_penalty: bool,
    jd_role: str | None,
    resume_role: str | None,
    role_alignment_score: float,
    evidence: dict[str, Any],
    req_ratio: float,
    pref_ratio: float,
    required_match: dict,
    preferred_match: dict,
    years: float,
    min_years_experience: Optional[float],
    degree: str,
    required_degree: Optional[str],
) -> dict[str, Any]:
    summary_bits = []
    concerns = []
    improvements = []

    if req_ratio >= 0.85:
        summary_bits.append("Matches most required skills with high confidence.")
    elif req_ratio >= 0.6:
        summary_bits.append("Covers several required skills, with some gaps.")
    else:
        summary_bits.append("Required skill coverage is limited.")

    if pref_ratio >= 0.5:
        summary_bits.append("Shows useful adjacent preferred experience.")
    if evidence["has_metrics"]:
        summary_bits.append("Includes quantified project impact.")

    missing_required = required_match["missing_skills"]
    missing_preferred = preferred_match["missing_skills"]

    if jd_role and resume_role and role_alignment_score < 0.5:
        concerns.append(f"Role focus appears more {resume_role} than {jd_role}.")
        improvements.append(f"Add more {jd_role}-focused project evidence.")

    if stack_penalty and jd_primary and resume_primary:
        concerns.append(
            f"Primary backend experience appears to be {resume_primary}, while the JD emphasizes {jd_primary}."
        )
        improvements.append(f"Add stronger {jd_primary}-based backend projects or production work.")

    if evidence["skill_only_risk"]:
        concerns.append("Many skills are listed without enough supporting project or experience evidence.")
        improvements.append("Tie listed tools to concrete projects, outcomes, or production responsibilities.")

    if missing_required:
        concerns.append("Missing required skills: " + ", ".join(missing_required[:4]) + ".")
        improvements.append("Make the missing required skills explicit in projects or experience.")

    data_tool_gaps = [s for s in ("spark", "hadoop") if s in missing_preferred]
    if data_tool_gaps:
        concerns.append("No explicit big data tools like Spark/Hadoop.")
        improvements.append("Show data pipeline, batch processing, Spark, or Hadoop experience.")
    elif missing_preferred:
        concerns.append("Some preferred skills are not explicit: " + ", ".join(missing_preferred[:3]) + ".")

    if min_years_experience is not None and years < min_years_experience:
        concerns.append(f"Experience is below the requested {min_years_experience:g}+ years.")

    if required_degree and required_degree != "None" and DEGREE_ORDER.get(degree, 0) < DEGREE_ORDER.get(required_degree, 0):
        concerns.append(f"Education is below the requested {required_degree} level.")

    if not improvements and missing_preferred:
        improvements.append("Add concrete examples for the preferred stack to improve confidence.")

    return {
        "score_summary": " ".join(summary_bits),
        "score_concerns": concerns[:4],
        "score_improvements": improvements[:4],
        "primary_backend_language": resume_primary,
        "jd_primary_backend_language": jd_primary,
        "resume_role_family": resume_role,
        "jd_role_family": jd_role,
    }


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

    # 🔥 FIX: better JD extraction
    if jd_skills is None:
        jd_skills = set(extract_jd_skills(job_desc_raw))
    if preferred_skills is None:
        preferred_skills = set()
    jd_skills = {
        normalize_skill(s)
        for s in jd_skills
        if isinstance(s, str) and not s.startswith("unknown:")
    }
    preferred_skills = {
        normalize_skill(s)
        for s in preferred_skills
        if isinstance(s, str) and not s.startswith("unknown:")
    }
    jd_primary_backend_language = _primary_backend_language(job_desc_raw, jd_skills)
    jd_role_family = _role_family(job_desc_raw, jd_skills | preferred_skills)

    LOWER_BOUND = 0.05
    UPPER_BOUND = 0.35

    results = []
    for i, raw in enumerate(resumes_raw):
        resume_skills = set(extract_skills(raw))
        evidence = _evidence_quality(raw, resume_skills)
        resume_role_family = _role_family(raw, resume_skills)
        role_alignment_score = _role_alignment(jd_role_family, resume_role_family)

        # 🔥 NEW SKILL MATCHING
        skill_result = match_skills(list(resume_skills), list(jd_skills))
        preferred_result = match_skills(list(resume_skills), list(preferred_skills))

        matched = skill_result["matched_skills"]
        weights_inf = skill_result["inference_weights"]

        # 🔥 DEBUG: Log skill matching for troubleshooting
        logger.debug(f"Resume {i+1} Skill Matching:")
        logger.debug(f"  JD Skills: {sorted(jd_skills)}")
        logger.debug(f"  Resume Skills: {sorted(resume_skills)}")
        logger.debug(f"  Matched: {matched}")
        logger.debug(f"  Inferred: {list(weights_inf.keys())}")
        logger.debug(f"  Missing: {skill_result['missing_skills']}")

        req_score = len(matched)
        req_score += sum(_confidence_credit(weights_inf.get(skill, 0)) for skill in skill_result["inferred_skills"])
        req_ratio = req_score / max(1, len(jd_skills)) if jd_skills else 0.0

        pref_score = len(preferred_result["matched_skills"])
        pref_score += sum(
            _confidence_credit(preferred_result["inference_weights"].get(skill, 0))
            for skill in preferred_result["inferred_skills"]
        )
        pref_ratio = pref_score / max(1, len(preferred_skills)) if preferred_skills else 0.0

        if jd_skills and preferred_skills:
            skills_score = (0.85 * req_ratio) + (0.15 * pref_ratio)
        elif jd_skills:
            skills_score = req_ratio
        else:
            skills_score = pref_ratio
        skills_score = max(0.0, min(1.0, skills_score))
        if evidence["skill_only_risk"]:
            skills_score *= 0.55
        elif evidence["has_metrics"] and evidence["has_project_evidence"]:
            skills_score = min(1.0, skills_score + 0.03)

        # EXPERIENCE
        exp_str = extract_experience(raw)[0]
        years = float(re.search(r"\d+(\.\d+)?", exp_str).group())
        if years == 0:
            exp_score = 0.5
        else:
            exp_score = min(1.0, years / experience_cap_years)

        meets_min_exp = None
        if min_years_experience is not None:
            meets_min_exp = years >= min_years_experience
            if not meets_min_exp:
                exp_score = min(exp_score, 0.5)
            else:
                exp_score = max(exp_score, min(1.0, years / max(min_years_experience, 1.0)))

        # EDUCATION
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
            else:
                edu_score = 1.0

        # RELEVANCE
        raw_sim = float(similarity_scores[i])
        semantic_overlap_score = max(0.0, min(1.0, (raw_sim - LOWER_BOUND) / (UPPER_BOUND - LOWER_BOUND)))
        skill_context_score = (0.75 * req_ratio) + (0.25 * pref_ratio)
        relevance_score = max(
            semantic_overlap_score,
            max(0.0, min(1.0, (0.62 * skill_context_score) + (0.38 * role_alignment_score) - 0.05)),
        )
        if evidence["skill_only_risk"]:
            relevance_score = min(relevance_score, 0.45)

        # FINAL
        raw_score = (
            weights["skills"] * skills_score
            + weights["experience"] * exp_score
            + weights["education"] * edu_score
            + weights["relevance"] * relevance_score
        )

        total_weight = sum(weights.values()) or 1.0
        final_normalized = raw_score / total_weight
        resume_primary_backend_language = _primary_backend_language(raw, resume_skills)
        stack_penalty = (
            jd_primary_backend_language is not None
            and resume_primary_backend_language is not None
            and jd_primary_backend_language != resume_primary_backend_language
        )
        if stack_penalty:
            has_jd_language = jd_primary_backend_language in resume_skills
            final_normalized *= 0.95 if has_jd_language else 0.90
        if evidence["skill_only_risk"]:
            final_normalized *= 0.70
        elif evidence["has_metrics"] and evidence["has_project_evidence"]:
            final_normalized *= 1.04
        final_normalized = max(0.0, min(1.0, final_normalized))
        final = final_normalized ** 0.7
        explicit_count = len(skill_result["matched_skills"]) + len(preferred_result["matched_skills"])
        inferred_count = len(skill_result["inferred_skills"]) + len(preferred_result["inferred_skills"])
        confidence_level = _confidence_level(
            inferred_count=inferred_count,
            explicit_count=explicit_count,
            evidence_score=evidence["score"],
            skill_only_risk=evidence["skill_only_risk"],
        )
        final_score = round(final * 100, 2)
        explanation = _explanation_for_candidate(
            jd_primary=jd_primary_backend_language,
            resume_primary=resume_primary_backend_language,
            stack_penalty=stack_penalty,
            jd_role=jd_role_family,
            resume_role=resume_role_family,
            role_alignment_score=role_alignment_score,
            evidence=evidence,
            req_ratio=req_ratio,
            pref_ratio=pref_ratio,
            required_match=skill_result,
            preferred_match=preferred_result,
            years=years,
            min_years_experience=min_years_experience,
            degree=degree,
            required_degree=required_degree,
        )

        results.append({
            "final_score":             final_score,
            "skills_score":            round(skills_score * 100, 1),
            "exp_score":               round(exp_score * 100, 1),
            "edu_score":               round(edu_score * 100, 1),
            "relevance_score":         round(relevance_score * 100, 1),
            "semantic_overlap_score":   round(semantic_overlap_score * 100, 1),
            "role_alignment_score":     round(role_alignment_score * 100, 1),
            "degree":                  degree,
            "years_experience":        round(years, 1),
            "experience_str":          exp_str,
            "resume_skills":           resume_skills,

            # 🔥 UPDATED OUTPUT
            "missing_required_skills": skill_result["missing_skills"],
            "matched_skills": sorted(set(skill_result["matched_skills"]) | set(skill_result["inferred_skills"])),
            "matched_preferred_skills": sorted(set(preferred_result["matched_skills"]) | set(preferred_result["inferred_skills"])),
            "inferred_skills": sorted(set(skill_result["inferred_skills"]) | set(preferred_result["inferred_skills"])),
            "confidence_level": confidence_level,
            "hiring_recommendation": _hiring_recommendation(final_score),
            **explanation,

            "meets_min_experience":    meets_min_exp,
            "meets_degree_req":        meets_degree_req,
        })

    return results
