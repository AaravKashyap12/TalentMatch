# Multi-stage build — keeps final image lean
# Stage 1: install deps + download models
# Stage 2: copy only what's needed into the runtime image

FROM python:3.11-slim AS builder

WORKDIR /app

# System deps for pdfplumber and spaCy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpoppler-cpp-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Pre-download spaCy model into the image (sentence-transformers removed)
COPY scripts/download_models.py scripts/download_models.py
RUN python scripts/download_models.py

# ---- Runtime stage ----
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages and cached models from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY api/     api/
COPY ml/      ml/
COPY db/      db/
COPY scripts/ scripts/

# Non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Single worker — Render free tier is single-core and 512 MB RAM.
# Multiple workers each load their own copy of spaCy (~50 MB each),
# which quickly exhausts the memory budget.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
