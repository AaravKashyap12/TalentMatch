import os
import PyPDF2
from ml.matcher import extract_experience, extract_education

RESUME_DIR = "test_resumes"

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
    return text

def main():
    if not os.path.exists(RESUME_DIR):
        print(f"Directory {RESUME_DIR} not found.")
        return

    print(f"{'Filename':<55} | {'Experience':<15} | {'Education':<10}")
    print("-" * 88)

    for filename in os.listdir(RESUME_DIR):
        if filename.lower().endswith(".pdf"):
            path = os.path.join(RESUME_DIR, filename)
            text = extract_text_from_pdf(path)
            exp = extract_experience(text)
            edu = extract_education(text)
            print(f"{filename:<55} | {str(exp):<15} | {edu:<10}")

if __name__ == "__main__":
    main()
