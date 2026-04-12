"""
Unit tests for ml/matcher.py — scoring engine, extractors, and ATS scorer.

Run with:  pytest tests/test_matcher.py -v
"""

import pytest
from ml.matcher import (
    calculate_ats_score,
    extract_education,
    extract_experience,
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
