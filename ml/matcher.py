import re
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


SKILLS_DB = [
    "python", "java", "c++", "c", "c#", "javascript", "typescript", "go",
    "rust", "swift", "kotlin", "php", "ruby", "scala", "r", "matlab",
    "html", "css", "react", "angular", "vue", "node.js", "next.js",
    "django", "flask", "fastapi", "spring boot",
    "machine learning", "deep learning", "data science", "nlp",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "ci/cd", "linux", "git", "github",
    "sql", "nosql", "mongodb", "postgresql", "mysql", "redis",
    "data structures", "algorithms", "system design", "oop"
]


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


def parse_date(date_str):
    date_str = date_str.strip().lower()
    if date_str in ["present", "current", "now"]:
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
            month_map = {
                "jan": 1, "feb": 2, "mar": 3, "apr": 4,
                "may": 5, "jun": 6, "jul": 7, "aug": 8,
                "sep": 9, "oct": 10, "nov": 11, "dec": 12
            }
            m = parts[0][:3]
            y = parts[-1]
            if m in month_map and y.isdigit():
                return datetime(int(y), month_map[m], 1)
    except Exception:
        pass

    return None


def merge_ranges(ranges):
    if not ranges:
        return []

    ranges.sort()
    merged = [ranges[0]]

    for start, end in ranges[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


EXPERIENCE_HEADERS = [
    "work experience",
    "experience",
    "employment history",
    "professional experience",
    "work history"
]

STOP_HEADERS = [
    "education",
    "projects",
    "skills",
    "certifications",
    "achievements",
    "leadership",
    "activities",
    "interests",
    "summary",
    "coursework",
    "hobbies"
]


def extract_experience(text):
    text_l = text.lower()

    # --------------------------------------------------
    # 1. Explicit experience claim (senior override)
    # --------------------------------------------------
    explicit = re.findall(
        r"(\d+)\s*\+?\s*(?:years|yrs)\s+(?:of\s+)?experience",
        text_l
    )
    if explicit:
        years = max(int(x) for x in explicit)
        return [f"{min(years, 40):.1f} Years"]

    # Remove specific PDF artifacts
    # Handle "w ork experience" specifically without strict boundaries (e.g. "JUnitW ORK EXPERIENCE")
    text_l = re.sub(r"(?i)w ork\s+experience", "work experience", text_l)
    text_l = re.sub(r"(?i)\bw ork\b", "work", text_l) # Fallback for other "w ork" occurrences
    text_l = re.sub(r"(?i)\be xperience\b", "experience", text_l)

    # --------------------------------------------------
    # 2. Locate WORK EXPERIENCE section
    # --------------------------------------------------
    # Split headers into strong (can assume header even if messy) and weak (need strict format)
    strong_headers = [
        "work experience", "employment history", "professional experience", "work history"
    ]
    weak_headers = ["experience"]

    start = None
    
    # Try strong headers first (allow them to be anywhere in line if followed by newline/colon)
    for h in strong_headers:
        # Match header, allowing preceding chars, but enforcing end of header (colon or newline)
        m = re.search(rf"{re.escape(h)}\s*(?::|\n|$)", text_l)
        if m:
            start = m.end()
            break
            
    # Try weak headers if no strong found (must be at start of line)
    if not start:
        for h in weak_headers:
            m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|\n|$)", text_l)
            if m:
                # For "Experience", prevent matching "My Experience..."
                # Check if the line is short (mostly just the header)
                line_start = text_l.rfind('\n', 0, m.start()) + 1
                line_content = text_l[line_start:m.end()].strip()
                if len(line_content) < len(h) + 5: # Allow small prefix like numbering
                    start = m.end()
                    break


    # ❌ No work section → zero experience
    if start is None:
        return ["0.0 Years"]

    end = len(text_l)
    for h in STOP_HEADERS:
        m = re.search(rf"(?:^|\n)\s*{h}\s*:?\s*(?:\n|$)", text_l[start:])
        if m:
            end = start + m.start()
            break

    section = text_l[start:end]

    # Remove student / club / volunteer roles
    NON_WORK_TERMS = [
        "club", "society", "captain", "volunteer",
        "student", "mentor", "committee", "sports"
    ]

    if any(term in section for term in NON_WORK_TERMS):
        # If no real job keywords exist, discard section
        if not re.search(r"(intern|engineer|developer|technician|assistant|analyst)", section):
            return ["0.0 Years"]


    # --------------------------------------------------
    # 3. STRICT job date parsing (inside work only)
    # --------------------------------------------------
    # Regex to capture full month names (january, jan, sept, september, etc.)
    months = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    
    date_pattern = (
        rf"(\b{months}\.?\s*\d{{4}}|\b\d{{1,2}}[/-]\d{{4}}|\b\d{{4}})"
        r"\s*(?:-|–|to)\s*"
        rf"(present|current|now|\b{months}\.?\s*\d{{4}}|\b\d{{1,2}}[/-]\d{{4}}|\b\d{{4}})"
    )

    matches = re.findall(date_pattern, section)
    ranges = []

    for s, e in matches:
        d1 = parse_date(s)
        d2 = parse_date(e)
        if d1 and d2 and d2 >= d1:
            ranges.append((d1, d2))

    if not ranges:
        return ["0.0 Years"]

    # --------------------------------------------------
    # 4. Merge overlaps (true experience timeline)
    # --------------------------------------------------
    ranges.sort()
    merged = [ranges[0]]

    for s, e in ranges[1:]:
        last_s, last_e = merged[-1]
        if s <= last_e:
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))

    total_months = 0
    for s, e in merged:
        total_months += (e.year - s.year) * 12 + (e.month - s.month)

    years = total_months / 12.0
    return [f"{min(years, 40):.1f} Years"]



def extract_education(text):
    # Clean stuck headers (e.g. "enhancementsEDUCATION" or "threats.EDUCATION")
    for header in ["EDUCATION", "SKILLS", "EXPERIENCE", "PROJECTS", "SUMMARY", "AWARDS"]:
        text = re.sub(rf"([a-z\.,])({header})", r"\1 \n\2", text)
        
    text_l = text.lower()
    
    # Clean artifacts
    text_l = re.sub(r"(?i)\be du\b", "edu", text_l)
    # Handle spaced out headers
    text_l = re.sub(r"(?i)\be\s+d\s+u\s+c\s+a\s+t\s+i\s+o\s+n\b", "education", text_l)
    text_l = re.sub(r"(?i)\bs\s+k\s+i\s+l\s+l\s+s\b", "skills", text_l)
    text_l = re.sub(r"(?i)\bp\s+r\s+o\s+j\s+e\s+c\s+t\s+s\b", "projects", text_l)
    text_l = re.sub(r"(?i)\ba\s+w\s+a\s+r\s+d\s+s\b", "awards", text_l)
    text_l = re.sub(r"(?i)\bs\s+u\s+m\s+m\s+a\s+r\s+y\b", "summary", text_l)

    headers = ["education", "academic history", "educational background", "academics"]
    
    # 1. Locate Education Section
    start = None
    for h in headers:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|\n|$)", text_l)
        if m:
            start = m.end()
            break
            
    if start is None:
        # Fallback: look for strong education keywords if no header found
        # checking specifically for degree mentions near university/college
        return "None"

    # Stop at next section
    others = [
        "experience", "work experience", "employment", "skills", 
        "projects", "certifications", "achievements", "summary", "awards"
    ]
    end = len(text_l)
    for h in others:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|\n|$)", text_l[start:])
        if m:
            end = start + m.start()
            break
            
    section = text_l[start:end]

    # 2. Parse Degree
    # PhD
    if re.search(r"\b(ph\.?d\.?|doctorate|doctor of)\b", section):
        return "PhD"
    
    # Master
    # Require dots for M.S. and M.A.; use special boundary handling because \b fails after dot
    if re.search(r"\b(master of|master's|masters|mba)\b|\b(m\.s\.|m\.a\.)(?=\W|$)", section):
        return "Master"
    
    # Bachelor
    if re.search(r"\b(bachelor of|bachelor's|bachelors|bs|ba)\b|\b(b\.?s\.?|b\.?a\.?|b\.?tech|b\.?eng)(?=\W|$)", section):
        return "Bachelor"
        
    # Associate
    if re.search(r"\b(associate|a\.?s\.?|a\.?a\.?|as|aa)\b", section):
        return "Associate"

    return "None"




def calculate_similarity(job_desc, resumes):
    if not resumes or not job_desc:
        return []

    docs = [job_desc] + resumes
    tfidf = TfidfVectorizer(stop_words="english")
    matrix = tfidf.fit_transform(docs)
    scores = cosine_similarity(matrix[0:1], matrix[1:])
    return scores[0].tolist()


def calculate_component_scores(
    job_desc_clean,
    resumes_clean,
    job_desc_raw,
    resumes_raw,
    weights
):
    similarity_scores = calculate_similarity(job_desc_clean, resumes_clean)
    jd_skills = set(extract_skills(job_desc_raw))
    results = []

    for i, raw in enumerate(resumes_raw):
        resume_skills = set(extract_skills(raw))

        skills_score = (
            len(jd_skills & resume_skills) / max(1, len(jd_skills))
            if jd_skills else min(1.0, len(resume_skills) / 8.0)
        )

        years = float(re.search(r"\d+(\.\d+)?", extract_experience(raw)[0]).group())
        exp_score = min(1.0, years / 10.0)

        degree = extract_education(raw)
        edu_map = {
            "PhD": 1.0,
            "Master": 0.8,
            "Bachelor": 0.6,
            "Associate": 0.4,
            "None": 0.0
        }
        edu_score = edu_map.get(degree, 0.0)

        raw_score = (
            weights["skills"] * skills_score +
            weights["experience"] * exp_score +
            weights["education"] * edu_score +
            weights["relevance"] * similarity_scores[i]
        )

        final = raw_score / (sum(weights.values()) or 1.0)

        results.append({
            "final_score": round(final * 100, 2),
            "skills_score": round(skills_score * 100, 1),
            "exp_score": round(exp_score * 100, 1),
            "edu_score": round(edu_score * 100, 1),
            "relevance_score": round(similarity_scores[i] * 100, 1)
        })

    return results


def calculate_ats_score(resume_text, job_keywords=None):
    text = resume_text.lower()
    wc = len(text.split())
    resume_skills = set(extract_skills(resume_text))

    skill_score = min(1.0, len(resume_skills) / 8.0)

    sections = ["experience", "education", "skills", "projects", "summary"]
    section_score = sum(1 for s in sections if s in text) / len(sections)

    years = float(re.search(r"\d+(\.\d+)?", extract_experience(resume_text)[0]).group())
    exp_score = 0.6 if years == 0 else 0.7 if years <= 2 else 0.85 if years <= 5 else 1.0

    parse_score = 0.3 if wc < 80 else 0.6 if wc < 150 else 0.85 if wc < 300 else 1.0

    final = (
        0.40 * skill_score +
        0.20 * section_score +
        0.15 * exp_score +
        0.15 * parse_score
    )

    return round(max(0.0, min(1.0, final)) * 100, 2)
