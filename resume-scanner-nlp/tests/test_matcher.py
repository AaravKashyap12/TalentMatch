from matcher import calculate_ats_score


def test_calculate_ats_score_keyword_and_experience():
    jd_keywords = ["Python", "Django", "AWS"]
    resume_text = """
    John Doe\n
    Experienced Software Engineer with 5 years of experience in Python and Django.\n
    Skills: Python, Django, REST API, AWS\n
    Education: B.S. Computer Science\n    """

    score = calculate_ats_score(resume_text, job_keywords=jd_keywords)
    assert isinstance(score, float)
    assert score > 50  # expect a reasonably high ATS score


def test_calculate_ats_score_short_resume_penalty():
    jd_keywords = ["Python"]
    resume_text = "John Doe\nContact: john@example.com"
    score = calculate_ats_score(resume_text, job_keywords=jd_keywords)
    assert isinstance(score, float)
    assert score < 20  # short resume should be penalized
