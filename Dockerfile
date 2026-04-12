# Multi-stage build — keeps final image lean
# Stage 1: install deps + download models
# Stage 2: copy only what's needed into the runtime image

FROM python:3.11-slim AS builder

WORKDIR /app

# System deps for pdfplumber, spaCy, and onnxruntime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpoppler-cpp-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Pre-download all models into the image so they're available at startup.
# HF_HOME controls where sentence-transformers caches models.
ENV HF_HOME=/app/.cache/huggingface
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
COPY --from=builder /app/.cache /app/.cache

# Copy application source
COPY api/     api/
COPY ml/      ml/
COPY db/      db/
COPY scripts/ scripts/

# Tell sentence-transformers and HuggingFace where the cached models live
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1

# Non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Render injects $PORT — fall back to 8000 for local docker run
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
