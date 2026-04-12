"""
Core scoring and extraction engine for TalentMatch.
2026 edition: sentence-transformer embeddings, spaCy NER skill extraction,
real ATS heuristics, robust experience parsing.
"""

import re
import logging
from datetime import datetime
from typing import List, Set, Dict, Any, Tuple, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SENTENCE TRANSFORMER — lazy loaded singleton  
# ---------------------------------------------------------------------------

_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("sentence-transformers model loaded: all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning("sentence-transformers unavailable (%s) — falling back to TF-IDF", e)
            _embedder = "tfidf"
    return _embedder


# ---------------------------------------------------------------------------
# SKILLS — hybrid: spaCy NER + curated seed list for precision
# ---------------------------------------------------------------------------

# Seed list used for high-precision matching of known technical terms.
# spaCy NER catches everything else.
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

# Synonyms for technical skills to ensure matching consistency
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


# FIX: blocklist of common false-positive NER entities — geographic places,
# generic company/institution words, and common resume words spaCy mislabels as ORG/PRODUCT.
_NER_BLOCKLIST = {
    # Cities / countries / regions commonly appearing on resumes
    "india","usa","us","uk","canada","australia","germany","france","singapore",
    "london","new york","san francisco","seattle","austin","chicago","boston",
    "bangalore","hyderabad","mumbai","delhi","chennai","pune","new delhi",
    "california","texas","washington","new york city","nyc","sf","la",
    # Generic company / institution words spaCy labels as ORG
    "university","college","institute","school","academy","foundation",
    "department","division","group","team","lab","laboratory","center","centre",
    "company","corporation","pvt","ltd","inc","llc","co","corp",
    # Generic resume section words
    "summary","experience","education","skills","projects","achievements",
    "certifications","references","work","employment","career","profile",
    # Months (sometimes tagged as entities)
    "january","february","march","april","may","june","july","august",
    "september","october","november","december",
    # Other common false positives
    "present","current","remote","full time","part time","contract","freelance",
    # ── Degree / education words — never a skill ──────────────────────────
    "bachelor","bachelors","bachelor's","bs","b.s","bsc","b.sc",
    "master","masters","master's","ms","m.s","msc","m.sc","mba","m.b.a",
    "phd","ph.d","doctorate","doctoral","associate","diploma","degree",
    "undergraduate","postgraduate","graduate","alumni","graduate student",
    "computer science","information technology","information systems",
    "electrical engineering","mechanical engineering","civil engineering",
    "mathematics","statistics","physics","biology","chemistry",
    # ── Job titles — never a skill ────────────────────────────────────────
    "software engineer","software developer","software development",
    "senior software engineer","junior software engineer",
    "full stack developer","backend developer","frontend developer",
    "data scientist","data analyst","data engineer","ml engineer",
    "product manager","project manager","engineering manager",
    "devops engineer","cloud engineer","security engineer",
    "web developer","mobile developer","ios developer","android developer",
    "intern","internship","trainee","fresher","entry level",
    # ── JD boilerplate phrases ────────────────────────────────────────────
    "required","preferred","must have","nice to have","excellent",
    "strong","proficient","familiarity","knowledge","understanding",
    "experience with","years of experience","minimum","plus","bonus",
    "ability","communication","problem solving","team player","collaborative",
    "analytical","detail oriented","fast learner","self motivated",
    "opportunity","position","role","responsibilities","requirements",
    "qualifications","candidate","applicant","hire","hiring",

}


def extract_skills(text: str) -> list:
    """
    Hybrid skill extraction:
    1. Seed list matching (high precision for known tech terms)
    2. spaCy NER to catch unknown tools, frameworks, libraries
       — GPE (geographic) entities excluded entirely
       — expanded blocklist suppresses city/company false positives
    """
    found = set()
    norm = _normalize(text)

    # 1 — Seed list
    for skill in SKILLS_SEED:
        ns = _normalize(skill)
        if len(ns.replace(" ", "")) <= 3:
            pat = rf"(?:^|\s){re.escape(ns)}(?:$|[\s,./])"
        else:
            pat = rf"\b{re.escape(ns)}\b"
        if re.search(pat, norm):
            found.add(skill)

    # 2 — spaCy NER: extract ORG and PRODUCT entities as candidate skills.
    # FIX: removed GPE label — geographic entities are never technical skills.
    # FIX: added _NER_BLOCKLIST check to suppress company/city false positives.
    try:
        from ml.nlp_utils import get_nlp
        nlp = get_nlp()
        doc = nlp(text[:8000])  # cap for performance
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT"):
                val = ent.text.strip()
                val_lower = val.lower()
                # Filter: only keep short entities that look like tools
                if 1 <= len(val.split()) <= 3 and len(val) <= 30:
                    # Check if any word in the entity matches the blocklist
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

    # Apply aliases (e.g., convert "k8s" to "kubernetes")
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

    # 1 — Explicit "X years experience" statements
    explicit = re.findall(
        r"(\d+\.?\d*)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+|relevant\s+)?experience",
        text_l
    )
    if explicit:
        years = max(float(x) for x in explicit)
        return [f"{min(years, 40):.1f} Years"]

    # 2 — Parse date ranges from experience section
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

    # Remove education/project bleed-through
    for h in ["education","projects","leadership","achievements"]:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|$)", work_section)
        if m:
            work_section = work_section[:m.start()]

    ranges = []
    for match in re.finditer(DATE_RANGE_PATTERN, work_section, re.IGNORECASE):
        s_str, e_str = match.groups()
        ctx = work_section[max(0, match.start()-150):match.end()+150]
        # FIX: use word boundaries so "founder" doesn't match "foundation",
        # "associate" doesn't match "association", etc.
        has_role = any(re.search(rf"\b{re.escape(role)}\b", ctx) for role in ROLE_KEYWORDS)
        if has_role:
            d1 = parse_date(s_str)
            d2 = parse_date(e_str)
            if d1 and d2 and d2 >= d1:
                    # Sanity check: a single role spanning >6 years is almost
                    # certainly an education date (e.g. "2023–2027") bleeding
                    # through the section boundary. Discard it.
                    span_years = (d2 - d1).days / 365.25
                    if span_years <= 6:
                        ranges.append((d1, d2))

    if not ranges:
        return ["0.0 Years"]

    # Merge overlapping ranges (handles concurrent roles / consulting)
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
    # FIX: require explicit dots in short abbreviations (b.e., b.a.) to prevent
    # matching common English words like "be" and "ba" mid-sentence.
    if re.search(
        r"\b(bachelor(?:s|\s+of|\s+'s)?|b\.s\.c?\.?|b\.tech|b\.e\.|b\.eng\.|b\.a\.)(?!\w)",
        section
    ):
        return "Bachelor"
    if re.search(r"\b(associate(?:\s+of|\s+degree)?|a\.s\.|a\.a\.)\b", section):
        return "Associate"
    return "None"


# ---------------------------------------------------------------------------
# SEMANTIC SIMILARITY — sentence-transformers with TF-IDF fallback
# ---------------------------------------------------------------------------

def calculate_similarity(job_desc: str, resumes: list) -> list:
    """
    Compute semantic similarity using sentence-transformers (all-MiniLM-L6-v2).
    Falls back to TF-IDF cosine similarity if transformers are unavailable.
    """
    if not resumes or not job_desc:
        return [0.0] * len(resumes)

    embedder = get_embedder()

    if embedder != "tfidf":
        try:
            texts = [job_desc] + resumes
            embeddings = embedder.encode(texts, show_progress_bar=False, batch_size=16)
            jd_emb = embeddings[0:1]
            res_embs = embeddings[1:]
            scores = cosine_similarity(jd_emb, res_embs)[0]
            return scores.tolist()
        except Exception as e:
            logger.warning("Embedding failed (%s), falling back to TF-IDF", e)

    # TF-IDF fallback
    from sklearn.feature_extraction.text import TfidfVectorizer
    docs = [job_desc] + resumes
    tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    matrix = tfidf.fit_transform(docs)
    scores = cosine_similarity(matrix[0:1], matrix[1:])
    return scores[0].tolist()


# ---------------------------------------------------------------------------
# REAL ATS SCORING
# ---------------------------------------------------------------------------

def calculate_ats_score(resume_raw: str, job_keywords: set = None) -> float:
    """
    ATS score based on actual ATS failure modes:
    - Contact info presence
    - Standard section headers
    - No tables/columns (detected via spacing patterns)
    - Keyword density vs JD
    - Length sanity
    - No garbled text (PDF extraction artifacts)
    - Standard date formats
    """
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

    # Contact info (10pts) — handle both normal and spaced-out PDF text
    email_compact = re.sub(r"\s+", "", text)  # collapse spaces for spaced PDFs
    check(5, bool(re.search(r"[\w.+-]+@[\w-]+\.\w+", email_compact)))
    check(5, bool(re.search(r"(\+?\d[\d\s\-().]{7,}\d)", text)))

    # Standard sections (30pts)
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

    # Parse quality checks (15pts)
    # Garble: excessive multi-spaces relative to word count
    garble_ratio = len(re.findall(r"\s{3,}", text)) / max(wc, 1)
    check(5, garble_ratio < 0.5)   # lenient — double-spaced PDFs are common
    # Spaced-out chars (k i s n a) = PDF extraction artifact, penalise lightly
    spaced_chars = len(re.findall(r"(?<=[a-zA-Z]) (?=[a-zA-Z])", text[:500]))
    check(5, spaced_chars < 20)
    non_ascii = sum(1 for c in text if ord(c) > 127) / max(len(text), 1)
    check(5, non_ascii < 0.05)

    # Length sanity: 300-1200 words is ATS sweet spot (10pts)
    check(5, wc >= 300)
    check(5, wc <= 1200)

    # Standard date formats (10pts)
    std_dates = re.findall(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}\b",
        text_l
    )
    bad_dates = re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", text_l)
    check(10, len(std_dates) >= len(bad_dates))

    # FIX: Keyword match vs JD — proportional scoring (0–25 pts).
    # Previously this was binary: kw_ratio >= 0.5 → 25pts, else 0pts.
    # A ratio of 0.49 was treated the same as 0.0, which is wrong.
    # Now we award points linearly proportional to the overlap ratio.
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
    """
    Score each resume against the JD across 4 components.
    Uses semantic embeddings for relevance, hybrid NER+seed for skills.
    """
    # Semantic similarity (single batch encode — efficient)
    similarity_scores = calculate_similarity(job_desc_raw, resumes_raw)

    if jd_skills is None:
        jd_skills = set(extract_skills(job_desc_raw))

    results = []
    for i, raw in enumerate(resumes_raw):
        resume_skills = set(extract_skills(raw))

        # FIX: when jd has no detectable skills, return 0.0 — not a padded reward.
        # The old fallback min(1.0, resume_skill_count/10) rewarded any resume
        # that listed 10+ skills regardless of relevance.
        if jd_skills:
            skills_score = len(jd_skills & resume_skills) / max(1, len(jd_skills))
        else:
            skills_score = 0.0

        # Experience score
        exp_str = extract_experience(raw)[0]
        years = float(re.search(r"\d+(\.\d+)?", exp_str).group())
        exp_score = min(1.0, years / experience_cap_years)

        # Education score
        degree = extract_education(raw)
        edu_map = {"PhD": 1.0, "Master": 0.8, "Bachelor": 0.6, "Associate": 0.4}
        edu_score = edu_map.get(degree, 0.3)

        # FIX: Relevance rescale — replaced (score - 0.1) / 0.6 which hard-zeroed
        # any cosine score below 0.1. The new formula uses empirical bounds for
        # all-MiniLM-L6-v2 on resume/JD pairs (typically 0.15–0.85), preserving
        # rank ordering and giving a meaningful 0–100 display value.
        raw_sim = float(similarity_scores[i])
        LOWER_BOUND = 0.15
        UPPER_BOUND = 0.85
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
            # Cache parsed experience string so routes.py doesn't re-call
            # extract_experience() — eliminates the duplicate parse.
            "experience_str":   exp_str,
            "resume_skills":    resume_skills,
        })

    return results

# ---------------------------------------------------------------------------
# STRUCTURED JD SCORING — extended version of calculate_component_scores
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
    """
    Extended scoring with structured JD support.

    Differences from calculate_component_scores
    -------------------------------------------
    - required_skills vs preferred_skills weighted separately (80/20 split)
    - min_years_experience: candidates below cap exp_score at 0.5
    - required_degree: candidates below halve their edu_score
    - missing_required_skills returned per candidate for frontend display
    - meets_min_experience / meets_degree_req flags returned explicitly
    """
    similarity_scores = calculate_similarity(job_desc_raw, resumes_raw)

    if jd_skills is None:
        jd_skills = set(extract_skills(job_desc_raw))
    if preferred_skills is None:
        preferred_skills = set()

    results = []
    for i, raw in enumerate(resumes_raw):
        resume_skills = set(extract_skills(raw))

        # Skills — required weighted 80%, preferred 20%
        if jd_skills or preferred_skills:
            req_ratio  = len(jd_skills & resume_skills) / max(1, len(jd_skills)) if jd_skills else 0.0
            pref_ratio = len(preferred_skills & resume_skills) / max(1, len(preferred_skills)) if preferred_skills else 0.0
            skills_score = (0.8 * req_ratio) + (0.2 * pref_ratio)
        else:
            skills_score = 0.0

        # Experience
        exp_str = extract_experience(raw)[0]
        years = float(re.search(r"\d+(\.\d+)?", exp_str).group())
        exp_score = min(1.0, years / experience_cap_years)

        meets_min_exp = None
        if min_years_experience is not None:
            meets_min_exp = years >= min_years_experience
            if not meets_min_exp:
                exp_score = min(exp_score, 0.5)

        # Education
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

        # Relevance
        raw_sim = float(similarity_scores[i])
        relevance_score = max(0.0, min(1.0, (raw_sim - 0.15) / 0.70))

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