"""
One-shot script: inspect existing users/keys and issue a fresh API key.
Writes the new key to web/.env and prints it to stdout.
"""
import sqlite3
import hashlib
import secrets
import os
from datetime import datetime, timezone
import uuid

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "talentmatch.db")
WEB_ENV = os.path.join(os.path.dirname(__file__), "..", "web", ".env")
ROOT_ENV = os.path.join(os.path.dirname(__file__), "..", ".env")

KEY_PREFIX = "tm_"
KEY_BYTES = 32

def _utcnow():
    return datetime.now(timezone.utc).isoformat()

def hash_key(raw):
    return hashlib.sha256(raw.encode()).hexdigest()

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# --- Show existing state ---
print("=== USERS ===")
try:
    for row in c.execute("SELECT id, email, is_active FROM users"):
        print(f"  id={row[0]}  email={row[1]}  active={row[2]}")
except Exception as e:
    print(f"Error reading users: {e}")

print("\n=== API KEYS ===")
try:
    for row in c.execute("SELECT id, user_id, prefix, is_active, key_hash FROM api_keys"):
        print(f"  id={row[0]}  user={row[1]}  prefix={row[2]}  active={row[3]}")
except Exception as e:
    print(f"Error reading api_keys: {e}")

# --- Ensure at least one active user exists ---
user_row = c.execute("SELECT id, email FROM users WHERE is_active=1 LIMIT 1").fetchone()
if not user_row:
    uid = str(uuid.uuid4())
    now = _utcnow()
    c.execute("INSERT INTO users (id, email, is_active, created_at) VALUES (?, ?, 1, ?)", (uid, "dev@talentmatch.local", now))
    conn.commit()
    user_row = (uid, "dev@talentmatch.local")
    print(f"\n[+] Created dev user: {uid}")

user_id = user_row[0]
print(f"\n--- Using user: {user_row[1]} ({user_id}) ---")

# --- Generate fresh key ---
raw_key = KEY_PREFIX + secrets.token_hex(KEY_BYTES)
hashed = hash_key(raw_key)

key_id = str(uuid.uuid4())
now = _utcnow()
c.execute(
    "INSERT INTO api_keys (id, user_id, key_hash, prefix, name, is_active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
    (key_id, user_id, hashed, raw_key[:8], "dev-local", now),
)
conn.commit()
conn.close()

print(f"\n[+] New API key generated: {raw_key}")
print(f"    Hash: {hashed}")

# --- Write web/.env (UTF-8, no BOM) ---
with open(WEB_ENV, "w", encoding="utf-8") as f:
    f.write(f"VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1\n")
    f.write(f"VITE_TM_API_KEY={raw_key}\n")
print(f"[+] Written to {WEB_ENV}")

# --- Write root .env (UTF-8, no BOM) ---
with open(ROOT_ENV, "w", encoding="utf-8") as f:
    f.write(f"DATABASE_URL=sqlite+aiosqlite:///./talentmatch.db\n")
    f.write(f"ADMIN_SECRET=talentmatch_admin_2026\n")
    f.write(f"CORS_ORIGINS=http://localhost:5173\n")
print(f"[+] Written to {ROOT_ENV}")

print("\n✅ Done! Restart both servers to pick up the new key.")
