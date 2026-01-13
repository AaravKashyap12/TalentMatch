import PyPDF2

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    except Exception:
        return ""

