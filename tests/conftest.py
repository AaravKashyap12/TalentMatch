"""
conftest.py — global pytest configuration.

Sets DATABASE_URL to an in-memory SQLite database before any app code
imports it, so tests never touch a real database.
"""

import os

# Must be set before db.session is imported
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_SECRET", "test-admin-secret")
