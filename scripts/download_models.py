#!/usr/bin/env python3
"""
Pre-download ML models into the Docker image so they are ready at startup.

NOTE: sentence-transformers has been removed to keep production memory usage low.
Only the spaCy en_core_web_sm model (~50 MB) is pre-downloaded now.

Usage
-----
  python scripts/download_models.py

Dockerfile build step
---------------------
  RUN python scripts/download_models.py
"""

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


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


if __name__ == "__main__":
    log.info("=== TalentMatch model pre-download ===")
    download_spacy()
    log.info("=== All models ready ===")
    log.info("NOTE: sentence-transformers removed — TF-IDF used for similarity.")
