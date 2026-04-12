import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Upload size limit (default 20 MB)
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20")) * 1024 * 1024

# FIX: global default was 30/minute while /scan/pdf was explicitly decorated at
# 10/minute — any future route would silently inherit 30/minute with no override.
# Set the global default to 10/minute to match the most restrictive endpoint.
# Individual routes can override upward (e.g. @limiter.limit("60/minute")) if needed.
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])