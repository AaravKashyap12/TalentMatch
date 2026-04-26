import logging

logger = logging.getLogger(__name__)

MAX_PAGES = 60  # Guard against huge PDFs hanging a worker

# PDF magic bytes: 0x25504446 = "%PDF"
PDF_MAGIC_BYTES = b"\x25\x50\x44\x46"


def is_valid_pdf(raw_bytes: bytes) -> bool:
    """
    Validate that the file starts with PDF magic bytes (%PDF).
    Returns True if valid PDF magic bytes found, False otherwise.
    """
    if len(raw_bytes) < 4:
        return False
    return raw_bytes[:4] == PDF_MAGIC_BYTES


def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extract plain text from a PDF file object.

    Strategy:
      1. Try pypdf (fast, handles most modern PDFs).
      2. Fall back to pdfplumber (slower but better on complex layouts).

    Returns an empty string if both attempts fail, and logs the reason.
    """
    # Read bytes once so both libraries can seek from the start.
    try:
        raw_bytes = uploaded_file.read()
    except Exception as exc:
        logger.error("Could not read uploaded file: %s", exc)
        return ""

    text = _try_pypdf(raw_bytes)
    if text.strip():
        return text

    logger.info("pypdf returned empty text — falling back to pdfplumber")
    text = _try_pdfplumber(raw_bytes)
    if text.strip():
        return text

    logger.warning("Both PDF extractors returned empty text")
    return ""


def _try_pypdf(raw_bytes: bytes) -> str:
    try:
        import io
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = reader.pages[:MAX_PAGES]
        parts = []
        for page in pages:
            content = page.extract_text()
            if content:
                parts.append(content)
        return "\n".join(parts)
    except Exception as exc:
        logger.warning("pypdf extraction failed: %s", exc)
        return ""



def _try_pdfplumber(raw_bytes: bytes) -> str:
    try:
        import io
        import pdfplumber

        parts = []
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages[:MAX_PAGES]:
                content = page.extract_text()
                if content:
                    parts.append(content)
        return "\n".join(parts)
    except Exception as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)
        return ""