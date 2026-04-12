import re
import logging

import spacy

import threading

logger = logging.getLogger(__name__)

# Lazy-loaded singleton with thread-safe lock
_nlp = None
_nlp_lock = threading.Lock()


def get_nlp():
    """Return the spaCy model, loading it once on first call (thread-safe)."""
    global _nlp
    if _nlp is None:
        with _nlp_lock:
            if _nlp is None:
                try:
                    _nlp = spacy.load("en_core_web_sm")
                    logger.info("spaCy model loaded: en_core_web_sm")
                except OSError:
                    from spacy.cli import download
                    logger.warning("en_core_web_sm not found — downloading…")
                    download("en_core_web_sm")
                    _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _preprocess(text: str) -> str:
    """Lowercase, strip URLs/emails, then remove characters that are neither
    alphabetic nor numeric nor whitespace.

    FIX: the original regex [^a-zA-Z\\s] stripped ALL digits, which caused
    "5 years experience", "Python 3", "GPT-4", "C++", "Node.js" to lose
    meaningful tokens before TF-IDF vectorisation and skill extraction.
    Numbers are now preserved so the downstream models see them.
    """
    text = text.lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\S+@\S+", "", text)
    # Keep letters, digits, and whitespace — strip everything else
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return text


def clean_text(text: str) -> str:
    """Clean and lemmatize a single text string."""
    if not text:
        return ""
    nlp = get_nlp()
    doc = nlp(_preprocess(text))
    tokens = [
        token.lemma_
        for token in doc
        if not token.is_stop and not token.is_punct and token.text.strip()
    ]
    return " ".join(tokens)


def clean_texts_batch(texts: list[str]) -> list[str]:
    """
    Clean and lemmatize a list of texts in one spaCy pass.
    3-5x faster than calling clean_text() in a loop.
    """
    if not texts:
        return []
    nlp = get_nlp()
    preprocessed = [_preprocess(t) for t in texts]
    results = []
    for doc in nlp.pipe(preprocessed, batch_size=16):
        tokens = [
            token.lemma_
            for token in doc
            if not token.is_stop and not token.is_punct and token.text.strip()
        ]
        results.append(" ".join(tokens))
    return results