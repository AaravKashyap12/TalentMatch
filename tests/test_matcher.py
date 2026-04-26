"""
Unit tests for ml/matcher.py — scoring engine, extractors, and ATS scorer.

Run with:  pytest tests/test_matcher.py -v
"""

import pytest
from ml.matcher import (
    calculate_ats_score,
    extract_education,
    extract_experience,
    extract_jd_skill_tiers,
    extract_skills,
    parse_date,
    calculate_component_scores_structured,
)


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_present_keywords(self):
        for kw in ("present", "current", "now", "ongoing", "till date"):
            d = parse_date(kw)
            assert d is not None
            assert d.year >= 2024

    def test_four_digit_year(self):
        d = parse_date("2020")
        assert d.year == 2020 and d.month == 1

    def test_month_year(self):
        d = parse_date("Jan 2021")
        assert d.year == 2021 and d.month == 1

    def test_month_year_full(self):
        d = parse_date("September 2019")
        assert d.year == 2019 and d.month == 9

    def test_mm_yyyy(self):
        d = parse_date("03/2022")
        assert d.year == 2022 and d.month == 3

    def test_garbage_returns_none(self):
        assert parse_date("not a date") is None
        assert parse_date("") is None


# ---------------------------------------------------------------------------
# extract_skills
# ---------------------------------------------------------------------------

class TestExtractSkills:
    def test_seed_skills_detected(self):
        text = "Experienced in Python, React, and PostgreSQL."
        skills = extract_skills(text)
        assert "python" in skills
        assert "react" in skills
        assert "postgresql" in skills

    def test_short_skills_need_word_boundary(self):
        # "go" skill should not match inside "going" or "algorithms"
        text = "I enjoy going for walks and working on algorithms."
        skills = extract_skills(text)
        assert "go" not in skills

    def test_go_detected_as_standalone(self):
        text = "Proficient in Go and Python."
        skills = extract_skills(text)
        assert "go" in skills

    def test_cities_not_extracted_as_skills(self):
        text = "Based in Hyderabad, India. Previously worked in New York."
        skills = extract_skills(text)
        assert "hyderabad" not in skills
        assert "india" not in skills
        assert "new york" not in skills

    def test_framework_variations(self):
        text = "Built APIs with FastAPI and Node.js. Used Next.js for frontend."
        skills = extract_skills(text)
        assert "fastapi" in skills
        assert "node.js" in skills
        assert "next.js" in skills

    def test_no_duplicate_skills(self):
        text = "Python Python python PYTHON"
        skills = extract_skills(text)
        assert skills.count("python") == 1


# ---------------------------------------------------------------------------
# extract_experience
# ---------------------------------------------------------------------------

class TestExtractExperience:
    def test_explicit_years_statement(self):
        text = "I have 5 years of professional experience in software development."
        result = extract_experience(text)
        assert result == ["5.0 Years"]

    def test_explicit_years_plus(self):
        text = "3+ years of relevant experience building distributed systems."
        result = extract_experience(text)
        assert result == ["3.0 Years"]

    def test_date_range_with_role(self):
        text = """
WORK EXPERIENCE
Software Engineer — Acme Corp
Jan 2020 – Jan 2022

"""
        result = extract_experience(text)
        years = float(result[0].split()[0])
        assert 1.8 <= years <= 2.2, f"Expected ~2 years, got {result[0]}"

    def test_no_experience_section(self):
        text = "John Doe\njohn@example.com\nEducation: B.Tech in CS"
        result = extract_experience(text)
        assert result == ["0.0 Years"]

    def test_cap_at_40_years(self):
        text = "50 years of experience in software."
        result = extract_experience(text)
        assert result == ["40.0 Years"]

    def test_overlapping_ranges_merged(self):
        # Two concurrent roles should not double-count
        text = """
WORK EXPERIENCE
Software Engineer — Company A
Jan 2020 – Jan 2022

Consultant — Company B
Jun 2020 – Jun 2021

"""
        result = extract_experience(text)
        years = float(result[0].split()[0])
        # Should be ~2 years (merged), not ~3 years (additive)
        assert years <= 2.5, f"Overlapping ranges should be merged; got {result[0]}"


# ---------------------------------------------------------------------------
# extract_education
# ---------------------------------------------------------------------------

class TestExtractEducation:
    def test_phd_detection(self):
        assert extract_education("PhD in Computer Science, MIT 2018") == "PhD"
        assert extract_education("Doctor of Philosophy, Stanford") == "PhD"

    def test_master_detection(self):
        assert extract_education("Master of Science in AI, 2020") == "Master"
        assert extract_education("M.Tech from IIT Bombay") == "Master"
        assert extract_education("MBA, Harvard Business School") == "Master"

    def test_bachelor_detection(self):
        assert extract_education("B.Tech in Computer Science, 2019") == "Bachelor"
        assert extract_education("Bachelor of Engineering") == "Bachelor"
        assert extract_education("B.Sc. in Mathematics") == "Bachelor"

    def test_be_does_not_match_common_words(self):
        # "be able to" must NOT trigger a Bachelor match
        text = "I am able to be responsible for system design. be proactive."
        result = extract_education(text)
        assert result == "None", f"'be' in prose incorrectly matched as Bachelor: {result}"

    def test_ba_does_not_match_mid_word(self):
        # "ba" in "database" must not trigger Bachelor
        text = "Worked on database optimisation and big data pipelines."
        result = extract_education(text)
        assert result == "None"

    def test_associate_detection(self):
        assert extract_education("Associate of Science in IT") == "Associate"

    def test_no_education_returns_none(self):
        assert extract_education("5 years of Python experience in fintech.") == "None"

    def test_phd_beats_master_in_same_text(self):
        text = "Started with a Master's degree, then completed a PhD in ML."
        assert extract_education(text) == "PhD"


# ---------------------------------------------------------------------------
# calculate_ats_score
# ---------------------------------------------------------------------------

class TestATSScore:
    def _good_resume(self):
        return """
John Doe
john@example.com  +91-9876543210

SUMMARY
Experienced software engineer with 5 years of experience.

EXPERIENCE
Software Engineer — Acme
Jan 2020 – Present

EDUCATION
B.Tech in Computer Science, 2019

SKILLS
Python, FastAPI, PostgreSQL, Docker

PROJECTS
Built a recommendation engine using scikit-learn.
"""

    def test_good_resume_scores_high(self):
        score = calculate_ats_score(self._good_resume())
        assert score >= 60, f"Well-formed resume should score >=60, got {score}"

    def test_keyword_match_is_proportional(self):
        resume = self._good_resume()
        # With half the keywords matched
        score_some = calculate_ats_score(resume, job_keywords={"python", "fastapi", "kubernetes", "terraform"})
        score_none = calculate_ats_score(resume, job_keywords={"kubernetes", "terraform", "ansible", "helm"})
        assert score_some > score_none, "Partial keyword match should score higher than zero match"

    def test_no_contact_info_penalised(self):
        bare = "Software Engineer with 5 years experience.\nSKILLS\nPython\nEXPERIENCE\nDeveloper\nEDUCATION\nB.Tech"
        score = calculate_ats_score(bare)
        full  = calculate_ats_score(self._good_resume())
        assert score < full

    def test_score_between_0_and_100(self):
        for text in ["", "x" * 5000, self._good_resume()]:
            score = calculate_ats_score(text)
            assert 0 <= score <= 100


# ---------------------------------------------------------------------------
# calculate_component_scores_structured
# ---------------------------------------------------------------------------

class TestStructuredScoring:
    WEIGHTS = {"skills": 0.75, "experience": 0.5, "education": 0.5, "relevance": 0.5}

    def test_missing_required_skills_listed(self):
        jd = "Looking for a Python and Kubernetes engineer."
        resume = "Experienced Python developer. Built Django and FastAPI services."
        results = calculate_component_scores_structured(
            job_desc_clean=jd,
            resumes_clean=[resume],
            job_desc_raw=jd,
            resumes_raw=[resume],
            weights=self.WEIGHTS,
            jd_skills={"python", "kubernetes"},
        )
        assert "kubernetes" in results[0]["missing_required_skills"]
        assert "python" not in results[0]["missing_required_skills"]

    def test_min_experience_penalty(self):
        jd = "Senior engineer role. 5 years minimum."
        junior = "Software Developer — Acme\nJan 2023 – Present\nPython, FastAPI"
        senior = "7 years of professional experience in software development."

        results = calculate_component_scores_structured(
            job_desc_clean=jd,
            resumes_clean=[junior, senior],
            job_desc_raw=jd,
            resumes_raw=[junior, senior],
            weights=self.WEIGHTS,
            min_years_experience=5.0,
        )
        junior_exp  = results[0]["exp_score"]
        senior_exp  = results[1]["exp_score"]
        assert junior_exp <= 50.0, f"Junior should be capped at 50 exp score, got {junior_exp}"
        assert senior_exp  > 50.0, f"Senior should not be capped, got {senior_exp}"
        assert results[0]["meets_min_experience"] == False  # noqa: E712
        assert results[1]["meets_min_experience"] == True   # noqa: E712

    def test_required_degree_penalty(self):
        jd = "PhD required for this research role."
        bachelors_resume = "B.Tech in Computer Science, IIT 2019. EXPERIENCE Software Engineer"
        phd_resume = "PhD in Machine Learning, Stanford 2022. EXPERIENCE Research Scientist"

        results = calculate_component_scores_structured(
            job_desc_clean=jd,
            resumes_clean=[bachelors_resume, phd_resume],
            job_desc_raw=jd,
            resumes_raw=[bachelors_resume, phd_resume],
            weights=self.WEIGHTS,
            required_degree="PhD",
        )
        assert results[0]["meets_degree_req"] == False  # noqa: E712
        assert results[1]["meets_degree_req"] == True   # noqa: E712
        assert results[0]["edu_score"] < results[1]["edu_score"]

    def test_preferred_skills_give_partial_credit(self):
        jd = "Python required. Knowledge of Rust preferred."
        resume_both   = "Experienced in Python and Rust development."
        resume_python = "Python developer with 5 years experience."

        results = calculate_component_scores_structured(
            job_desc_clean=jd,
            resumes_clean=[resume_both, resume_python],
            job_desc_raw=jd,
            resumes_raw=[resume_both, resume_python],
            weights=self.WEIGHTS,
            jd_skills={"python"},
            preferred_skills={"rust"},
        )
        assert results[0]["skills_score"] > results[1]["skills_score"], \
            "Candidate with preferred skill should score higher"

    def test_final_score_between_0_and_100(self):
        jd = "Looking for a full-stack engineer with React and Node.js."
        resume = "Full-stack developer. React, Node.js, PostgreSQL. B.Tech CS."
        results = calculate_component_scores_structured(
            job_desc_clean=jd,
            resumes_clean=[resume],
            job_desc_raw=jd,
            resumes_raw=[resume],
            weights=self.WEIGHTS,
        )
        assert 0 <= results[0]["final_score"] <= 100

    def test_jd_tiers_keep_preferred_examples_out_of_missing_required(self):
        jd = """
Job Title: Software Engineer - Backend (Python / Data Systems)

Responsibilities:
Design, develop, and maintain RESTful APIs and backend services.
Participate in code reviews and system design discussions.

## 🧩 Required Skills:
Strong proficiency in Python
Experience with data structures and algorithms
Familiarity with SQL and database design
Knowledge of REST APIs and backend frameworks (e.g., Flask, Django, FastAPI)
Understanding of version control systems (Git)
Basic understanding of Linux environments

## 🌟 Preferred / Good-to-Have:
Experience with cloud platforms (AWS / GCP / Azure)
Exposure to Docker or containerization
Knowledge of distributed systems or microservices architecture
Familiarity with CI/CD pipelines
Experience handling large-scale data processing (Spark, Hadoop, etc.)

Hidden Testing Angles:
Identify missing skills like no Docker, no API experience, no database work.
"""
        resume = """
Backend and full stack developer. Built scalable backend services with Python,
FastAPI and Express. Designed REST endpoints backed by PostgreSQL and SQL.
Solved data structures and algorithms problems. Uses Linux, GitHub, Docker,
CI/CD, Kafka, Redis and distributed systems patterns.
Education: B.Tech in Computer Science.
"""
        tiers = extract_jd_skill_tiers(jd)
        assert "cloud platform" in tiers["preferred"]
        assert "spark" in tiers["preferred"]
        assert "hadoop" in tiers["preferred"]
        assert "data processing" in tiers["preferred"]
        assert "data processing" not in tiers["required"]
        assert "software engineer" not in tiers["required"]

        results = calculate_component_scores_structured(
            job_desc_clean=jd,
            resumes_clean=[resume],
            job_desc_raw=jd,
            resumes_raw=[resume],
            weights=self.WEIGHTS,
            jd_skills=set(tiers["required"]),
            preferred_skills=set(tiers["preferred"]) | set(tiers["implicit"]),
            min_years_experience=0,
            required_degree="Bachelor",
        )
        result = results[0]
        assert result["missing_required_skills"] == []
        assert "backend framework" in result["matched_skills"]
        assert "rest api" in result["matched_skills"]
        assert "git" in result["matched_skills"]
        assert "data processing" in result["matched_preferred_skills"]
        assert "microservices" in result["matched_preferred_skills"]
        assert result["final_score"] >= 85

    def test_backend_jd_ranks_backend_above_ml_above_keyword_spam(self):
        jd = """
Required Skills:
Python, data structures, algorithms, SQL, REST APIs, backend frameworks,
version control systems, Linux

Preferred / Good-to-Have:
Cloud platforms, Docker, distributed systems, microservices, CI/CD,
large-scale data processing with Spark or Hadoop
"""
        backend = """
EXPERIENCE
Software Engineer - Backend
Built Python FastAPI services with PostgreSQL and Redis on Linux.
Designed REST APIs, optimized p95 latency by 42%, and sustained 2.4K RPS.
Implemented CI/CD with GitHub Actions, Docker, Kafka event streaming, and
distributed system components for production workloads.
PROJECTS
Scaled backend job processing and improved throughput by 3x.
EDUCATION
B.Tech Computer Science.
"""
        ml_heavy = """
EXPERIENCE
Machine Learning Engineer
Built TensorFlow and PyTorch models using Pandas, NumPy and scikit-learn.
Trained recommendation models, evaluated experiments in Jupyter, and deployed
batch notebooks. Familiar with Python and SQL.
EDUCATION
B.Tech Computer Science.
"""
        keyword_spam = """
SKILLS
Python, FastAPI, Django, Flask, SQL, PostgreSQL, Docker, Kubernetes, AWS, GCP,
Azure, Spark, Hadoop, Kafka, Redis, microservices, distributed systems, Linux,
Git, GitHub Actions, CI/CD, REST APIs, algorithms, data structures.
"""
        tiers = extract_jd_skill_tiers(jd)
        results = calculate_component_scores_structured(
            job_desc_clean=jd,
            resumes_clean=[backend, ml_heavy, keyword_spam],
            job_desc_raw=jd,
            resumes_raw=[backend, ml_heavy, keyword_spam],
            weights=self.WEIGHTS,
            jd_skills=set(tiers["required"]),
            preferred_skills=set(tiers["preferred"]) | set(tiers["implicit"]),
            min_years_experience=0,
            required_degree="Bachelor",
        )

        backend_score, ml_score, spam_score = [r["final_score"] for r in results]
        assert backend_score > ml_score > spam_score
        assert results[0]["confidence_level"] == "High"
        assert results[2]["confidence_level"] == "Low"
        assert results[2]["hiring_recommendation"] in {"Consider", "Reject"}

    def test_java_microservices_jd_phrase_variants_do_not_create_false_gaps(self):
        jd = """
Required Skills:
Strong proficiency in Java
Solid understanding of data structures and algorithms
Experience with Spring Boot or similar backend frameworks
Familiarity with REST APIs and API design principles
Experience with SQL and database systems
Knowledge of Linux environments
Understanding of microservices architecture

Preferred / Good-to-Have:
Cloud platforms, Docker and container orchestration
Kafka / RabbitMQ or other messaging systems
Distributed systems and NoSQL databases
"""
        resume = """
EXPERIENCE
Backend Engineer
Built Java Spring Boot microservices and REST APIs with API design reviews.
Used SQL databases on Linux, optimized latency, and practiced data structures
and algorithms. Integrated Kafka and RabbitMQ messaging, Docker, AWS,
distributed systems patterns, and MongoDB.
EDUCATION
B.Tech Computer Science.
"""
        jd_skills = {
            "java",
            "data structures and algorithms",
            "backend framework",
            "rest api",
            "api design principles",
            "sql",
            "linux environments",
            "microservices architecture",
        }
        preferred = {
            "cloud platforms",
            "docker",
            "container orchestration",
            "messaging systems",
            "distributed system",
            "nosql databases",
        }

        results = calculate_component_scores_structured(
            job_desc_clean=jd,
            resumes_clean=[resume],
            job_desc_raw=jd,
            resumes_raw=[resume],
            weights=self.WEIGHTS,
            jd_skills=jd_skills,
            preferred_skills=preferred,
            min_years_experience=0,
            required_degree="Bachelor",
        )

        result = results[0]
        assert result["missing_required_skills"] == []
        assert "api design" in result["matched_skills"]
        assert "linux" in result["matched_skills"]
        assert "microservices" in result["matched_skills"]
        assert "messaging system" in result["matched_preferred_skills"]
        assert "nosql database" in result["matched_preferred_skills"]
        assert result["final_score"] >= 85

    def test_score_stability_under_light_rewording(self):
        jd = """
Required Skills:
Python, SQL, REST APIs, backend frameworks, Git, Linux

Preferred / Good-to-Have:
Docker, microservices, distributed systems, CI/CD
"""
        jd_reworded = """
We need a backend engineer who can build HTTP API services with Python,
work with relational databases, use version control, and operate comfortably
in Linux environments. Docker, service-oriented architecture, distributed
systems, and deployment pipelines are useful extras.
"""
        resume = """
SUMMARY
Backend engineer with 4 years of professional experience.

EXPERIENCE
Software Engineer - Backend
Built Python FastAPI REST APIs backed by PostgreSQL and SQL on Linux.
Used Git, Docker and GitHub Actions CI/CD to deploy microservices.
Improved p95 latency by 30% and handled 1.2K requests per second.

EDUCATION
B.Tech in Computer Science.
"""
        resume_reworded = """
SUMMARY
Software backend developer with four years of production experience.

EXPERIENCE
Backend Software Engineer
Implemented API endpoints in Python using FastAPI, PostgreSQL, and SQL.
Worked daily on Linux, tracked changes with Git, containerized services with
Docker, and maintained CI/CD workflows through GitHub Actions.
Raised throughput by 30% for a high-traffic service.

EDUCATION
Bachelor of Technology, Computer Science.
"""

        common = {
            "weights": self.WEIGHTS,
            "jd_skills": {"python", "sql", "rest api", "backend framework", "git", "linux"},
            "preferred_skills": {"docker", "microservices", "distributed systems", "ci/cd"},
            "min_years_experience": 0,
            "required_degree": "Bachelor",
        }
        original = calculate_component_scores_structured(
            job_desc_clean=jd,
            resumes_clean=[resume],
            job_desc_raw=jd,
            resumes_raw=[resume],
            **common,
        )[0]["final_score"]
        perturbed = calculate_component_scores_structured(
            job_desc_clean=jd_reworded,
            resumes_clean=[resume_reworded],
            job_desc_raw=jd_reworded,
            resumes_raw=[resume_reworded],
            **common,
        )[0]["final_score"]

        assert abs(original - perturbed) <= 5.0
