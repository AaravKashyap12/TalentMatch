"""Groq-generated candidate overviews from structured scoring facts."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import structlog

from api import config

log = structlog.get_logger()


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


def coerce_overview_payload(payload: dict[str, Any]) -> dict[int, str]:
    """Return rank -> overview for valid short overview strings."""
    raw_items = payload.get("overviews")
    if not isinstance(raw_items, list):
        raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        return {}

    overviews: dict[int, str] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        rank = item.get("rank")
        overview = item.get("overview")
        if not isinstance(rank, int) or not isinstance(overview, str):
            continue
        overview = " ".join(overview.split())
        if not overview:
            continue
        overviews[rank] = overview[:420]
    return overviews


def _candidate_fact(candidate: Any, rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "filename": getattr(candidate, "filename", None),
        "score": getattr(candidate, "final_score", None),
        "recommendation": getattr(candidate, "hiring_recommendation", None),
        "confidence": getattr(candidate, "confidence_level", None),
        "skills_score": getattr(candidate, "skills_score", None),
        "relevance_score": getattr(candidate, "relevance_score", None),
        "experience": getattr(candidate, "experience", None),
        "degree": getattr(candidate, "degree", None),
        "candidate_stack": getattr(candidate, "primary_backend_language", None),
        "jd_stack": getattr(candidate, "jd_primary_backend_language", None),
        "matched_skills": (getattr(candidate, "matched_skills", None) or [])[:18],
        "missing_required": (getattr(candidate, "missing_required_skills", None) or [])[:8],
        "watchouts": (getattr(candidate, "score_concerns", None) or [])[:4],
        "improvements": (getattr(candidate, "score_improvements", None) or [])[:3],
    }


def _build_messages(
    role_title: str,
    jd_required: list[str],
    jd_preferred: list[str],
    candidates: list[Any],
) -> list[dict[str, str]]:
    facts = {
        "role_title": role_title,
        "required_skills": jd_required[:30],
        "preferred_skills": jd_preferred[:30],
        "candidates": [
            _candidate_fact(candidate, rank)
            for rank, candidate in enumerate(candidates, start=1)
        ],
    }
    return [
        {
            "role": "system",
            "content": (
                "You write concise recruiter-facing candidate overviews. "
                "Use only the provided structured facts. Do not invent missing "
                "skills, companies, years, education, or experience. Each overview "
                "must be 1-2 sentences, clear, and decision-oriented. Mention key "
                "strength and the biggest risk if one exists. Return only JSON with "
                "an overviews array: [{rank: number, overview: string}]."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(facts, ensure_ascii=True),
        },
    ]


async def generate_candidate_overviews(
    role_title: str,
    jd_required: list[str],
    jd_preferred: list[str],
    candidates: list[Any],
) -> dict[int, str]:
    """Generate AI overview text keyed by candidate rank."""
    if not candidates or not config.ENABLE_GROQ_OVERVIEWS or not config.GROQ_API_KEY:
        return {}

    url = f"{config.GROQ_BASE_URL.rstrip('/')}/chat/completions"
    body = {
        "model": config.GROQ_MODEL,
        "messages": _build_messages(role_title, jd_required, jd_preferred, candidates),
        "temperature": 0.2,
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
            log.warning("groq_overview_invalid_json")
            return {}
        return coerce_overview_payload(payload)
    except Exception as exc:  # pragma: no cover - network/provider failures vary
        log.warning("groq_overview_failed", error=str(exc))
        return {}
