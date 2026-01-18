import PyPDF2


def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        pages_text = []

        for page in pdf_reader.pages:
            content = page.extract_text()
            if content:
                pages_text.append(content)

        return "\n".join(pages_text)
    except Exception:
        return ""
