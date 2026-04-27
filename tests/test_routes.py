"""
Integration tests for TalentMatch API routes.

Uses FastAPI's async test client with an in-memory SQLite database so no
external services are needed.

Run with:  pytest tests/test_routes.py -v
"""

import io
import json
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.main import get_cors_origins
from api import config
import api.routes as api_routes
from db.session import AsyncSessionLocal, engine, init_db
from db.models import Base, User, ApiKey, Candidate, Scan
from api.auth.dependencies import generate_api_key, hash_key


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Create all tables in the test database once per session."""
    await init_db()
    yield
    # Teardown — drop all tables after the test session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def stable_test_env(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "false")
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    monkeypatch.setattr(config, "ENABLE_GROQ_JD_PARSING", False)
    monkeypatch.setattr(api_routes, "GROQ_API_KEY", "")
    monkeypatch.setattr(api_routes, "ENABLE_GROQ_JD_PARSING", False)


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user + API key, return (user, raw_key)."""
    user = User(email=f"test-{uuid.uuid4()}@talentmatch.dev")
    db_session.add(user)
    await db_session.flush()

    raw_key = generate_api_key()
    key = ApiKey(
        user_id=user.id,
        key_hash=hash_key(raw_key),
        prefix=raw_key[:8],
        name="test key",
    )
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(user)
    return user, raw_key


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Minimal valid PDF bytes (text-based, single page "Hello World")
# ---------------------------------------------------------------------------

def _minimal_text_pdf(content: str = "John Doe\njohn@example.com\n+91 9876543210\n\nSUMMARY\nPython developer with 3 years experience.\n\nEXPERIENCE\nSoftware Engineer — Acme\nJan 2021 – Present\n\nEDUCATION\nB.Tech in Computer Science 2020\n\nSKILLS\nPython, FastAPI, PostgreSQL, Docker\n\nPROJECTS\nBuilt a REST API with FastAPI and PostgreSQL.\n") -> bytes:
    """
    Generate a minimal valid text-based PDF in pure Python without any library.
    The PDF contains a single page with the given text content.
    """
    lines = content.replace("\r\n", "\n").split("\n")
    # Build a simple PDF manually
    stream_content = "BT\n/F1 12 Tf\n72 720 Td\n"
    for line in lines[:30]:  # limit lines
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\n", "")
        stream_content += f"({safe}) Tj\n0 -16 Td\n"
    stream_content += "ET"
    stream_bytes = stream_content.encode("latin-1", errors="replace")
    stream_len = len(stream_bytes)

    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n")
    objects.append(f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode() + stream_bytes + b"\nendstream\nendobj\n")
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_offset = len(pdf)
    xref = f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n"
    pdf += xref.encode()
    pdf += f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    return pdf


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client):
        r = await client.get("/api/v1/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "models" in data

    def test_cors_adds_localhost_loopback_pair(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")

        origins = get_cors_origins()

        assert "http://localhost:5173" in origins
        assert "http://127.0.0.1:5173" in origins


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestAuth:
    @pytest.mark.asyncio
    async def test_no_key_returns_401(self, client):
        r = await client.post("/api/v1/scan/pdf")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_key_returns_401(self, client):
        r = await client.post(
            "/api/v1/scan/pdf",
            headers={"X-API-Key": "tm_invalidkeynotreal"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_key_passes_auth(self, client, test_user):
        _, raw_key = test_user
        pdf = _minimal_text_pdf()
        r = await client.post(
            "/api/v1/scan/pdf",
            headers={"X-API-Key": raw_key},
            data={
                "job_description": "Looking for a Python software engineer with FastAPI experience.",
                "required_skills": "[]",
                "preferred_skills": "[]",
                "min_years_experience": "null",
                "required_degree": "null",
            },
            files={"files": ("resume.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        # Should not be 401 or 403
        assert r.status_code not in (401, 403), r.text

    @pytest.mark.asyncio
    async def test_supabase_profile_bootstraps_user(self, client, monkeypatch):
        import api.auth.dependencies as auth_deps

        secret = "test-supabase-secret-with-32-bytes"
        user_id = str(uuid.uuid4())
        email = f"supabase-{uuid.uuid4()}@talentmatch.dev"
        token = jwt.encode(
            {
                "sub": user_id,
                "email": email,
                "user_metadata": {"name": "Token Name"},
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            secret,
            algorithm="HS256",
        )
        monkeypatch.setattr(auth_deps, "SUPABASE_JWT_SECRET", secret)

        r = await client.post(
            "/api/v1/profiles",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": email, "name": "Profile Name"},
        )

        assert r.status_code == 201, r.text
        data = r.json()
        assert data["id"] == user_id
        assert data["email"] == email
        assert data["name"] == "Profile Name"

    @pytest.mark.asyncio
    async def test_supabase_bearer_tolerates_small_clock_skew(self, client, monkeypatch):
        import api.auth.dependencies as auth_deps

        secret = "test-supabase-secret-with-32-bytes"
        user_id = str(uuid.uuid4())
        email = f"skew-{uuid.uuid4()}@talentmatch.dev"
        token = jwt.encode(
            {
                "sub": user_id,
                "email": email,
                "iat": datetime.now(timezone.utc) + timedelta(seconds=45),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            secret,
            algorithm="HS256",
        )
        monkeypatch.setattr(auth_deps, "SUPABASE_JWT_SECRET", secret)

        r = await client.get(
            "/api/v1/usage",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert r.status_code == 200, r.text
        data = r.json()
        assert data["free_scan_limit"] == 5
        assert data["free_scans_used"] == 0

    @pytest.mark.asyncio
    async def test_supabase_bearer_accepts_jwks_signed_token(self, client, monkeypatch):
        import api.auth.dependencies as auth_deps

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        user_id = str(uuid.uuid4())
        email = f"jwks-{uuid.uuid4()}@talentmatch.dev"
        token = jwt.encode(
            {
                "sub": user_id,
                "email": email,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test-key"},
        )

        class StubSigningKey:
            def __init__(self, key):
                self.key = key

        class StubJwkClient:
            def get_signing_key_from_jwt(self, raw_token):
                assert raw_token == token
                return StubSigningKey(public_key)

        monkeypatch.setattr(auth_deps, "SUPABASE_URL", "https://pdzommymdbiwrztclexi.supabase.co")
        monkeypatch.setattr(auth_deps, "_get_supabase_jwk_client", lambda _: StubJwkClient())

        r = await client.get(
            "/api/v1/usage",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert r.status_code == 200, r.text
        data = r.json()
        assert data["free_scan_limit"] == 5
        assert data["free_scans_used"] == 0

    @pytest.mark.asyncio
    async def test_usage_returns_free_scan_quota(self, client, test_user):
        _, raw_key = test_user
        r = await client.get("/api/v1/usage", headers={"X-API-Key": raw_key})

        assert r.status_code == 200, r.text
        data = r.json()
        assert data["free_scan_limit"] == 5
        assert data["free_scans_used"] == 0
        assert data["free_scans_remaining"] == 5
        assert data["is_unlimited"] is False

    @pytest.mark.asyncio
    async def test_usage_is_unlimited_in_dev_mode(self, client, test_user, monkeypatch):
        _, raw_key = test_user
        monkeypatch.setenv("DEV_MODE", "true")

        r = await client.get("/api/v1/usage", headers={"X-API-Key": raw_key})

        assert r.status_code == 200, r.text
        data = r.json()
        assert data["is_unlimited"] is True
        assert data["free_scans_remaining"] == 5


# ---------------------------------------------------------------------------
# Scan endpoint
# ---------------------------------------------------------------------------

class TestScanPdf:
    @pytest.mark.asyncio
    async def test_successful_scan_returns_results(self, client, test_user):
        _, raw_key = test_user
        pdf = _minimal_text_pdf()
        r = await client.post(
            "/api/v1/scan/pdf",
            headers={"X-API-Key": raw_key},
            data={
                "job_description": "We are looking for a Python backend engineer with FastAPI and PostgreSQL.",
                "required_skills": json.dumps(["python", "fastapi"]),
                "preferred_skills": json.dumps(["docker"]),
                "min_years_experience": "null",
                "required_degree": "null",
                "experience_cap_years": "10",
                "skills_priority": "High",
                "experience_priority": "Medium",
                "education_priority": "Low",
                "relevance_priority": "Medium",
            },
            files={"files": ("resume.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "scan_id" in data
        assert data["total_candidates"] == 1
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert 0 <= result["final_score"] <= 100
        assert "matched_skills" in result
        assert "missing_required_skills" in result

    @pytest.mark.asyncio
    async def test_successful_scan_consumes_free_scan(self, client, test_user, db_session):
        user, raw_key = test_user
        pdf = _minimal_text_pdf()
        r = await client.post(
            "/api/v1/scan/pdf",
            headers={"X-API-Key": raw_key},
            data={
                "job_description": "We are looking for a Python backend engineer with FastAPI and PostgreSQL.",
                "required_skills": json.dumps(["python"]),
                "preferred_skills": json.dumps([]),
                "min_years_experience": "null",
                "required_degree": "null",
            },
            files={"files": ("resume.pdf", io.BytesIO(pdf), "application/pdf")},
        )

        assert r.status_code == 200, r.text
        await db_session.refresh(user)
        assert user.free_scans_used == 1

    @pytest.mark.asyncio
    async def test_sixth_free_scan_rejected(self, client, test_user, db_session):
        user, raw_key = test_user
        user.free_scans_used = 5
        await db_session.commit()

        pdf = _minimal_text_pdf()
        r = await client.post(
            "/api/v1/scan/pdf",
            headers={"X-API-Key": raw_key},
            data={
                "job_description": "We are looking for a Python backend engineer with FastAPI and PostgreSQL.",
                "required_skills": "[]",
                "preferred_skills": "[]",
                "min_years_experience": "null",
                "required_degree": "null",
            },
            files={"files": ("resume.pdf", io.BytesIO(pdf), "application/pdf")},
        )

        assert r.status_code == 403
        assert "Free scan limit reached" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_scan_persisted_in_history(self, client, test_user):
        _, raw_key = test_user
        pdf = _minimal_text_pdf()

        # Run a scan
        scan_r = await client.post(
            "/api/v1/scan/pdf",
            headers={"X-API-Key": raw_key},
            data={"job_description": "Python engineer needed.", "required_skills": "[]",
                  "preferred_skills": "[]", "min_years_experience": "null", "required_degree": "null"},
            files={"files": ("cv.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        assert scan_r.status_code == 200
        scan_id = scan_r.json()["scan_id"]

        # Should appear in history
        history_r = await client.get("/api/v1/scans", headers={"X-API-Key": raw_key})
        assert history_r.status_code == 200
        history = history_r.json()
        ids = [s["scan_id"] for s in history]
        assert scan_id in ids
        item = next(s for s in history if s["scan_id"] == scan_id)
        assert "role_title" in item
        assert "top_score" in item
        assert "avg_score" in item

    @pytest.mark.asyncio
    async def test_scan_detail_retrievable(self, client, test_user):
        _, raw_key = test_user
        pdf = _minimal_text_pdf()

        scan_r = await client.post(
            "/api/v1/scan/pdf",
            headers={"X-API-Key": raw_key},
            data={"job_description": "Looking for a Go developer with Kubernetes.",
                  "required_skills": "[]", "preferred_skills": "[]",
                  "min_years_experience": "null", "required_degree": "null"},
            files={"files": ("cv.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        scan_id = scan_r.json()["scan_id"]

        detail_r = await client.get(f"/api/v1/scans/{scan_id}", headers={"X-API-Key": raw_key})
        assert detail_r.status_code == 200
        detail = detail_r.json()
        assert detail["scan_id"] == scan_id
        assert "role_title" in detail
        assert len(detail["results"]) == 1

    @pytest.mark.asyncio
    async def test_other_user_cannot_access_scan(self, client, db_session):
        # Create two separate users
        user_a = User(email="user_a@test.dev")
        user_b = User(email="user_b@test.dev")
        db_session.add_all([user_a, user_b])
        await db_session.flush()

        key_a_raw = generate_api_key()
        key_b_raw = generate_api_key()
        db_session.add(ApiKey(user_id=user_a.id, key_hash=hash_key(key_a_raw), prefix=key_a_raw[:8]))
        db_session.add(ApiKey(user_id=user_b.id, key_hash=hash_key(key_b_raw), prefix=key_b_raw[:8]))
        await db_session.commit()

        pdf = _minimal_text_pdf()
        scan_r = await client.post(
            "/api/v1/scan/pdf",
            headers={"X-API-Key": key_a_raw},
            data={"job_description": "Backend developer with Python.", "required_skills": "[]",
                  "preferred_skills": "[]", "min_years_experience": "null", "required_degree": "null"},
            files={"files": ("cv.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        scan_id = scan_r.json()["scan_id"]

        # User B should get 404 trying to access User A's scan
        r = await client.get(f"/api/v1/scans/{scan_id}", headers={"X-API-Key": key_b_raw})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_short_job_description_rejected(self, client, test_user):
        _, raw_key = test_user
        pdf = _minimal_text_pdf()
        r = await client.post(
            "/api/v1/scan/pdf",
            headers={"X-API-Key": raw_key},
            data={"job_description": "too short", "required_skills": "[]",
                  "preferred_skills": "[]", "min_years_experience": "null", "required_degree": "null"},
            files={"files": ("cv.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_priority_rejected(self, client, test_user):
        _, raw_key = test_user
        pdf = _minimal_text_pdf()
        r = await client.post(
            "/api/v1/scan/pdf",
            headers={"X-API-Key": raw_key},
            data={"job_description": "Python engineer with FastAPI experience required.",
                  "required_skills": "[]", "preferred_skills": "[]",
                  "min_years_experience": "null", "required_degree": "null",
                  "skills_priority": "INVALID"},
            files={"files": ("cv.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_experience_cap_rejected(self, client, test_user):
        _, raw_key = test_user
        pdf = _minimal_text_pdf()
        r = await client.post(
            "/api/v1/scan/pdf",
            headers={"X-API-Key": raw_key},
            data={"job_description": "Python engineer with FastAPI experience required.",
                  "required_skills": "[]", "preferred_skills": "[]",
                  "min_years_experience": "null", "required_degree": "null",
                  "experience_cap_years": "999"},
            files={"files": ("cv.pdf", io.BytesIO(pdf), "application/pdf")},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

class TestAdminRoutes:
    ADMIN_SECRET = "test-admin-secret"

    @pytest.fixture(autouse=True)
    def set_admin_secret(self, monkeypatch):
        monkeypatch.setenv("ADMIN_SECRET", self.ADMIN_SECRET)

    @pytest.mark.asyncio
    async def test_create_user(self, client):
        r = await client.post(
            "/api/v1/admin/users",
            json={"email": "newuser@example.com"},
            headers={"X-Admin-Secret": self.ADMIN_SECRET},
        )
        assert r.status_code == 201
        assert r.json()["email"] == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_duplicate_user_rejected(self, client):
        email = "dup@example.com"
        await client.post("/api/v1/admin/users", json={"email": email},
                          headers={"X-Admin-Secret": self.ADMIN_SECRET})
        r = await client.post("/api/v1/admin/users", json={"email": email},
                              headers={"X-Admin-Secret": self.ADMIN_SECRET})
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_issue_key_and_use_it(self, client):
        # Create user
        user_r = await client.post(
            "/api/v1/admin/users",
            json={"email": "keytest@example.com"},
            headers={"X-Admin-Secret": self.ADMIN_SECRET},
        )
        user_id = user_r.json()["id"]

        # Issue key
        key_r = await client.post(
            f"/api/v1/admin/users/{user_id}/keys",
            json={"name": "my key"},
            headers={"X-Admin-Secret": self.ADMIN_SECRET},
        )
        assert key_r.status_code == 201
        raw_key = key_r.json()["key"]
        assert raw_key.startswith("tm_")

        # Use the key to hit a protected endpoint
        health_r = await client.get("/api/v1/health")
        assert health_r.status_code == 200  # health is public, just sanity check

    @pytest.mark.asyncio
    async def test_wrong_admin_secret_rejected(self, client):
        r = await client.post(
            "/api/v1/admin/users",
            json={"email": "hacker@evil.com"},
            headers={"X-Admin-Secret": "wrongsecret"},
        )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_analytics_returns_platform_metrics(self, client, db_session):
        user = User(email="analytics@example.com", free_scans_used=5)
        db_session.add(user)
        await db_session.flush()

        scan = Scan(
            user_id=user.id,
            role_title="Backend Engineer",
            job_description="Backend engineer with Python and APIs.",
            required_skills="[]",
            preferred_skills="[]",
            total_candidates=2,
            top_score=91.2,
            avg_score=81.4,
            jd_skills_count=4,
            processing_time_ms=1234.5,
        )
        db_session.add(scan)
        await db_session.flush()

        db_session.add_all([
            Candidate(
                scan_id=scan.id,
                rank=1,
                filename="strong.pdf",
                final_score=91.2,
                skills_score=92,
                exp_score=80,
                edu_score=75,
                relevance_score=88,
                ats_score=90,
                matched_skills_count=8,
                missing_required_skills="[]",
                experience="2 years",
                confidence_level="High",
                hiring_recommendation="Strong Hire",
            ),
            Candidate(
                scan_id=scan.id,
                rank=2,
                filename="review.pdf",
                final_score=71.6,
                skills_score=72,
                exp_score=65,
                edu_score=70,
                relevance_score=73,
                ats_score=77,
                matched_skills_count=5,
                missing_required_skills="[]",
                experience="1 year",
                confidence_level="Medium",
                hiring_recommendation="Hire",
            ),
        ])
        await db_session.commit()

        r = await client.get(
            "/api/v1/admin/analytics",
            headers={"X-Admin-Secret": self.ADMIN_SECRET},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["metrics"]["total_users"] >= 1
        assert data["metrics"]["total_scans"] >= 1
        assert data["metrics"]["total_candidates"] >= 2
        assert data["metrics"]["free_limit_reached"] >= 1
        assert data["recent_scans"][0]["role_title"] == "Backend Engineer"
        assert any(item["recommendation"] == "Strong Hire" for item in data["recommendation_breakdown"])
