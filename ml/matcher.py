import re
from datetime import datetime

from dateutil import parser as date_parser
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


SKILLS_DB = [
    "Python",
    "Java",
    "C++",
    "C",
    "C#",
    "JavaScript",
    "TypeScript",
    "Go",
    "Rust",
    "Swift",
    "Kotlin",
    "PHP",
    "Ruby",
    "Scala",
    "R",
    "Matlab",
    "Dart",
    "Lua",
    "Perl",
    "Shell",
    "Bash",
    "HTML",
    "CSS",
    "React",
    "Angular",
    "Vue",
    "Next.js",
    "Node.js",
    "Django",
    "Flask",
    "FastAPI",
    "Spring Boot",
    "ASP.NET",
    "Laravel",
    "Ruby on Rails",
    "Tailwind",
    "Bootstrap",
    "jQuery",
    "GraphQL",
    "REST API",
    "Machine Learning",
    "Deep Learning",
    "Data Science",
    "NLP",
    "Computer Vision",
    "TensorFlow",
    "PyTorch",
    "Keras",
    "Scikit-learn",
    "Pandas",
    "NumPy",
    "Matplotlib",
    "Seaborn",
    "OpenCV",
    "Hugging Face",
    "LLM",
    "Generative AI",
    "NLTK",
    "Spacy",
    "Jupyter",
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "Terraform",
    "Ansible",
    "Jenkins",
    "Git",
    "GitHub",
    "GitLab",
    "CI/CD",
    "Linux",
    "Unix",
    "Nginx",
    "Apache",
    "Heroku",
    "Vercel",
    "Netlify",
    "SQL",
    "NoSQL",
    "MongoDB",
    "PostgreSQL",
    "MySQL",
    "Oracle",
    "Redis",
    "Cassandra",
    "Elasticsearch",
    "DynamoDB",
    "Firebase",
    "Snowflake",
    "Databricks",
    "Algorithms",
    "Data Structures",
    "System Design",
    "OOP",
    "Functional Programming",
    "Agile",
    "Scrum",
    "Jira",
    "Trello",
    "Unit Testing",
    "Selenium",
    "Postman",
    "Swagger",
]


def extract_skills(text):
    found_skills = []
    text_lower = text.lower()

    for skill in SKILLS_DB:
        skill_lower = skill.lower()

        if len(skill) <= 3:
            pattern = rf"(?:^|\s){re.escape(skill_lower)}(?:$|[\s,.])"
        else:
            pattern = rf"\b{re.escape(skill_lower)}\b"

        if re.search(pattern, text_lower):
            found_skills.append(skill)

    return list(set(found_skills))


def parse_date(date_str):
    date_str = date_str.strip().lower()

    if date_str in {"present", "current", "now", "date", "till date", "today"}:
        return datetime.now()

    if re.match(r"^\d{4}$", date_str):
        try:
            return datetime(int(date_str), 1, 1)
        except Exception:
            pass

    try:
        return date_parser.parse(
            date_str,
            default=datetime(datetime.now().year, 1, 1),
        )
    except Exception:
        return None


def calculate_duration_in_years(start_str, end_str):
    start_date = parse_date(start_str)
    end_date = parse_date(end_str)

    if not start_date or not end_date or end_date < start_date:
        return 0.0

    diff = end_date - start_date
    return round(diff.days / 365.25, 2)


EXPERIENCE_HEADERS = [
    "work experience",
    "professional experience",
    "experience",
    "employment",
    "employment history",
    "work history",
]

STOP_HEADERS = [
    "education",
    "projects",
    "skills",
    "certifications",
    "achievements",
    "leadership",
    "interests",
    "hobbies",
    "languages",
    "summary",
]


def extract_experience(text):
    text_lower = text.lower()
    start_idx = None

    for header in EXPERIENCE_HEADERS:
        pattern = rf"(?:^|\n)\s*{re.escape(header)}\s*:?\s*(?:\n|$)"
        match = re.search(pattern, text_lower)
        if match:
            start_idx = match.end()
            break

    if start_idx is None:
        return ["0 Years"]

    end_idx = len(text_lower)

    for header in STOP_HEADERS:
        pattern = rf"(?:^|\n)\s*{re.escape(header)}\s*:?\s*(?:\n|$)"
        match = re.search(pattern, text_lower[start_idx:])
        if match:
            end_idx = start_idx + match.start()
            break

    experience_text = text_lower[start_idx:end_idx]

    date_ranges = re.findall(
        r"(19\d{2}|20\d{2})\s*[-–]\s*(present|current|19\d{2}|20\d{2})",
        experience_text,
    )

    total_years = 0.0
    current_year = datetime.now().year

    for start, end in date_ranges:
        start_year = int(start)
        end_year = current_year if end in {"present", "current"} else int(end)

        if end_year >= start_year:
            total_years += end_year - start_year

    if total_years < 0.5:
        return ["0 Years"]

    return [f"{round(min(total_years, 40), 1)} Years"]


def calculate_similarity(job_desc, resumes_texts):
    if not job_desc or not resumes_texts:
        return []

    documents = [job_desc] + resumes_texts
    tfidf = TfidfVectorizer(stop_words="english")
    matrix = tfidf.fit_transform(documents)

    similarities = cosine_similarity(matrix[0:1], matrix[1:])
    return similarities[0].tolist()


def calculate_component_scores(
    job_desc,
    resumes_texts,
    job_desc_raw,
    resumes_raw,
    weights,
):
    if not job_desc or not resumes_texts:
        return []

    similarity_scores = calculate_similarity(job_desc, resumes_texts)
    jd_skills = set(extract_skills(job_desc_raw))
    results = []

    for i, resume_raw in enumerate(resumes_raw):
        resume_skills = set(extract_skills(resume_raw))

        if jd_skills:
            skills_score = len(jd_skills & resume_skills) / len(jd_skills)
        else:
            skills_score = len(resume_skills) / 20.0

        skills_score = min(1.0, skills_score)

        exp_list = extract_experience(resume_raw)
        max_exp = 0.0

        for e in exp_list:
            match = re.search(r"(\d+(?:\.\d+)?)", e)
            if match:
                try:
                    max_exp = max(max_exp, float(match.group(1)))
                except Exception:
                    pass

        exp_score = min(1.0, max_exp / 10.0)

        text_lower = resume_raw.lower()
        edu_score = 0.0

        if any(
            k in text_lower
            for k in ["bachelor", "degree", "college", "university", "bs"]
        ):
            edu_score = 0.5
        if any(k in text_lower for k in ["master", "phd", "m.tech", "ms"]):
            edu_score = 1.0
        elif "education" in text_lower:
            edu_score = 0.3

        raw_score = (
            weights["skills"] * skills_score
            + weights["experience"] * exp_score
            + weights["education"] * edu_score
            + weights["relevance"] * similarity_scores[i]
        )

        total_weight = sum(weights.values())
        final_score = raw_score / total_weight if total_weight else 0.0

        results.append(
            {
                "final_score": round(final_score * 100, 2),
                "skills_score": round(skills_score * 100, 1),
                "exp_score": round(exp_score * 100, 1),
                "edu_score": round(edu_score * 100, 1),
                "relevance_score": round(similarity_scores[i] * 100, 1),
            }
        )

    return results


def calculate_ats_score(resume_text, job_keywords=None):
    if not resume_text or not isinstance(resume_text, str):
        return 0.0

    text = resume_text.lower()
    words = text.split()
    wc = len(words)

    resume_skills = {s.lower() for s in extract_skills(resume_text)}

    if job_keywords:
        jd_skills = {k.lower() for k in job_keywords}
        match_ratio = len(resume_skills & jd_skills) / max(1, len(jd_skills))

        if match_ratio >= 0.6:
            skill_score = 1.0
        elif match_ratio >= 0.4:
            skill_score = 0.85
        elif match_ratio >= 0.25:
            skill_score = 0.7
        else:
            skill_score = match_ratio
    else:
        skill_score = min(1.0, len(resume_skills) / 8.0)

    sections = [
        "experience",
        "education",
        "skills",
        "projects",
        "certifications",
        "summary",
    ]
    section_score = sum(1 for s in sections if s in text) / len(sections)

    years = 0.0
    for e in extract_experience(resume_text):
        match = re.search(r"(\d+(?:\.\d+)?)", e)
        if match:
            try:
                years = max(years, float(match.group(1)))
            except Exception:
                pass

    if years == 0:
        exp_score = 0.6
    elif years <= 2:
        exp_score = 0.7
    elif years <= 5:
        exp_score = 0.85
    else:
        exp_score = 1.0

    if wc < 80:
        parse_score = 0.3
    elif wc < 150:
        parse_score = 0.6
    elif wc < 300:
        parse_score = 0.85
    else:
        parse_score = 1.0

    project_hits = sum(
        kw in text
        for kw in [
            "designed",
            "implemented",
            "optimized",
            "scalable",
            "distributed",
            "latency",
            "throughput",
            "rps",
            "ci/cd",
            "docker",
            "kubernetes",
            "aws",
        ]
    )

    project_bonus = 0.12 if project_hits >= 6 else 0.08 if project_hits >= 3 else 0.0

    penalty = 0.0
    if wc < 60:
        penalty += 0.1
    if len(resume_skills) > 40:
        penalty += 0.1

    penalty = min(0.2, penalty)

    final_score = (
        0.40 * skill_score
        + 0.20 * section_score
        + 0.15 * exp_score
        + 0.15 * parse_score
        + project_bonus
        - penalty
    )

    return round(max(0.0, min(1.0, final_score)) * 100, 2)
