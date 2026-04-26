import os
from slowapi import Limiter
from slowapi.util import get_remote_address

MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20")) * 1024 * 1024
MAX_FILES_PER_SCAN = int(os.getenv("MAX_FILES_PER_SCAN", "15"))
FREE_SCAN_LIMIT = int(os.getenv("FREE_SCAN_LIMIT", "5"))

ENABLE_GROQ_JD_PARSING = os.getenv("ENABLE_GROQ_JD_PARSING", "true").lower() in {
    "1",
    "true",
    "yes",
}
ENABLE_GROQ_OVERVIEWS = os.getenv("ENABLE_GROQ_OVERVIEWS", "true").lower() in {
    "1",
    "true",
    "yes",
}
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_TIMEOUT_SECONDS = float(os.getenv("GROQ_TIMEOUT_SECONDS", "8"))
GROQ_MAX_JD_CHARS = int(os.getenv("GROQ_MAX_JD_CHARS", "6000"))


def is_dev_mode() -> bool:
    return os.getenv("DEV_MODE", "false").lower() == "true"


# Default 10/minute; individual routes can override upward
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])
