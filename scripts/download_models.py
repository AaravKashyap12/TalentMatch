#!/usr/bin/env python3
"""
Pre-download all ML models so they are baked into the deployment image.

Run this during Docker build / Render build step — NOT at runtime.
This eliminates the 30-60 second cold-start delay caused by downloading
the sentence-transformer model on first request.

Usage
-----
  python scripts/download_models.py

Render build command (render.yaml)
-----------------------------------
  pip install -r requirements.txt && python scripts/download_models.py
"""

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# Ensure results are cached in the same dir as the runtime image
os.environ["HF_HOME"] = "/app/.cache/huggingface"


def download_spacy():
    log.info("Checking spaCy model en_core_web_sm ...")
    try:
        import spacy
        spacy.load("en_core_web_sm")
        log.info("  spaCy model already present.")
    except OSError:
        log.info("  Downloading en_core_web_sm ...")
        from spacy.cli import download
        download("en_core_web_sm")
        log.info("  Done.")


def download_sentence_transformer():
    model_name = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
    log.info("Checking sentence-transformer model: %s ...", model_name)
    try:
        from sentence_transformers import SentenceTransformer
        # Loading the model here triggers the download if not cached
        model = SentenceTransformer(model_name)
        # Run a dummy encode to verify ONNX export works
        _ = model.encode(["test sentence"], show_progress_bar=False)
        log.info("  Model loaded and verified OK.")
    except Exception as e:
        log.error("  Failed to load sentence-transformer: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    log.info("=== TalentMatch model pre-download ===")
    download_spacy()
    download_sentence_transformer()
    log.info("=== All models ready ===")
