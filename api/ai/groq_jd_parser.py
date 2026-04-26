"""Groq-assisted JD parsing with deterministic fallback guards.

This module only sends the job description and user-entered skill tags to Groq.
Resume text stays inside the existing local scoring pipeline.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import structlog

from api import config
from pipeline.skills import extract_jd_skill_tiers, normalize_skill

log = structlog.get_logger()

_ROLE_CONTEXT = {
    "software engineer",
    "backend developer",
    "backend engineer",
    "full stack developer",
    "full stack engineer",
    "data systems",
    "candidate",
}


def _as_skill_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()

    skills: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        normalized = normalize_skill(value)
        if not normalized or normalized in _ROLE_CONTEXT:
            continue
        if len(normalized) > 60:
            continue
        skills.add(normalized)
    return skills


def _extract_json_object(content: str) -> dict[str, Any] | None:
    try:
        data = json.loads(content)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def coerce_groq_tiers(
    payload: dict[str, Any],
    jd_text: str,
    explicit_required: list[str] | None = None,
    explicit_preferred: list[str] | None = None,
) -> dict[str, list[str]]:
    """Normalize AI output and merge it with the deterministic parser.

    Deterministic section parsing acts as a safety rail. If it saw a skill in a
    preferred or implicit section, Groq cannot promote that skill to required.
    """
    deterministic = extract_jd_skill_tiers(jd_text, explicit_required, explicit_preferred)

    det_required = set(deterministic["required"])
    det_preferred = set(deterministic["preferred"])
    det_implicit = set(deterministic["implicit"])

    ai_required = _as_skill_set(payload.get("required"))
    ai_preferred = _as_skill_set(payload.get("preferred"))
    ai_implicit = _as_skill_set(payload.get("implicit"))

    explicit_req = _as_skill_set(explicit_required or [])
    explicit_pref = _as_skill_set(explicit_preferred or [])

    required = det_required | ai_required | explicit_req
    preferred = det_preferred | ai_preferred | explicit_pref
    implicit = det_implicit | ai_implicit

    required -= det_preferred | det_implicit | preferred
    required |= explicit_req
    preferred -= required
    implicit -= required | preferred

    return {
        "required": sorted(required),
        "preferred": sorted(preferred),
        "implicit": sorted(implicit),
    }


def _build_messages(
    jd_text: str,
    explicit_required: list[str] | None,
    explicit_preferred: list[str] | None,
) -> list[dict[str, str]]:
    clipped_jd = jd_text[: config.GROQ_MAX_JD_CHARS]
    return [
        {
            "role": "system",
            "content": (
                "You parse recruiting job descriptions into skill tiers. "
                "Return only valid JSON with three array fields: required, "
                "preferred, implicit. Do not include job titles, seniority, "
                "locations, benefits, responsibilities, or generic traits as skills. "
                "Examples inside a preferred section remain preferred. "
                "Examples inside parentheses like 'Flask, Django, FastAPI' should be "
                "collapsed to a requirement concept when appropriate, such as "
                "'backend framework'."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "job_description": clipped_jd,
                    "explicit_required_skills": explicit_required or [],
                    "explicit_preferred_skills": explicit_preferred or [],
                },
                ensure_ascii=True,
            ),
        },
    ]


async def parse_jd_skill_tiers_with_groq(
    jd_text: str,
    explicit_required: list[str] | None = None,
    explicit_preferred: list[str] | None = None,
) -> dict[str, list[str]] | None:
    """Return Groq-enhanced JD skill tiers, or None when AI is unavailable."""
    if not config.ENABLE_GROQ_JD_PARSING or not config.GROQ_API_KEY:
        return None

    url = f"{config.GROQ_BASE_URL.rstrip('/')}/chat/completions"
    body = {
        "model": config.GROQ_MODEL,
        "messages": _build_messages(jd_text, explicit_required, explicit_preferred),
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    try:
        async with httpx.AsyncClient(timeout=config.GROQ_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {config.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        payload = _extract_json_object(content)
        if payload is None:
            log.warning("groq_jd_parse_invalid_json")
            return None
        return coerce_groq_tiers(payload, jd_text, explicit_required, explicit_preferred)
    except Exception as exc:  # pragma: no cover - network/provider failures vary
        log.warning("groq_jd_parse_failed", error=str(exc))
        return None
