import PyPDF2
import os

RESUME_DIR = "test_resumes"
TARGETS = [
    "computer-science-resume-example.pdf"
]

def main():
    for name in TARGETS:
        path = os.path.join(RESUME_DIR, name)
        try:
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                out_name = f"debug_{name}.txt"
                with open(out_name, "w", encoding="utf-8") as out:
                    out.write(text)
                print(f"Dumped text to {out_name}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
