import pytest

from api import config
from api.ai.groq_jd_parser import (
    coerce_groq_tiers,
    parse_jd_skill_tiers_with_groq,
)
from api.ai.groq_overview import coerce_overview_payload


def test_groq_tiers_do_not_promote_preferred_skills_to_required():
    jd = """
Required Skills:
Python, SQL, REST APIs, backend frameworks, Git, Linux

Preferred / Good-to-Have:
Docker, Spark, Hadoop, cloud platforms
"""
    payload = {
        "required": ["Python", "Spark", "Hadoop", "Software Engineer"],
        "preferred": ["Docker"],
        "implicit": ["REST APIs"],
    }

    tiers = coerce_groq_tiers(payload, jd)

    assert "python" in tiers["required"]
    assert "spark" not in tiers["required"]
    assert "hadoop" not in tiers["required"]
    assert "software engineer" not in tiers["required"]
    assert "spark" in tiers["preferred"]
    assert "hadoop" in tiers["preferred"]


def test_groq_tiers_honor_explicit_required_skills():
    jd = "We need backend services and API work. Docker is a bonus."
    payload = {
        "required": [],
        "preferred": ["Docker", "Python"],
        "implicit": ["REST APIs"],
    }

    tiers = coerce_groq_tiers(
        payload,
        jd,
        explicit_required=["Python"],
        explicit_preferred=["Docker"],
    )

    assert "python" in tiers["required"]
    assert "docker" in tiers["preferred"]
    assert "python" not in tiers["preferred"]


@pytest.mark.asyncio
async def test_groq_parser_returns_none_without_key(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_GROQ_JD_PARSING", True)
    monkeypatch.setattr(config, "GROQ_API_KEY", "")

    tiers = await parse_jd_skill_tiers_with_groq("Required Skills: Python")

    assert tiers is None


def test_groq_overview_payload_is_sanitized():
    payload = {
        "overviews": [
            {"rank": 1, "overview": " Strong Java backend fit.  Main risk is limited production years. "},
            {"rank": "2", "overview": "bad rank"},
            {"rank": 3, "overview": ""},
        ]
    }

    overviews = coerce_overview_payload(payload)

    assert overviews == {
        1: "Strong Java backend fit. Main risk is limited production years."
    }
