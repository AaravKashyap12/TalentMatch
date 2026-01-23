import re

def extract_education(text):
    # Clean stuck headers (e.g. "enhancementsEDUCATION")
    # Insert newline before capitalized headers if they follow a lowercase letter or punctuation
    for header in ["EDUCATION", "SKILLS", "EXPERIENCE", "PROJECTS", "SUMMARY", "AWARDS"]:
        text = re.sub(rf"([a-z\.,])({header})", r"\1 \n\2", text)
        
    text_l = text.lower()
    
    # Clean artifacts
    text_l = re.sub(r"(?i)\be du\b", "edu", text_l)
    # Handle spaced out headers
    text_l = re.sub(r"(?i)\be\s+d\s+u\s+c\s+a\s+t\s+i\s+o\s+n\b", "education", text_l)
    text_l = re.sub(r"(?i)\bs\s+k\s+i\s+l\s+l\s+s\b", "skills", text_l)
    text_l = re.sub(r"(?i)\bp\s+r\s+o\s+j\s+e\s+c\s+t\s+s\b", "projects", text_l)
    text_l = re.sub(r"(?i)\ba\s+w\s+a\s+r\s+d\s+s\b", "awards", text_l)
    text_l = re.sub(r"(?i)\bs\s+u\s+m\s+m\s+a\s+r\s+y\b", "summary", text_l)

    print("DEBUG: Cleaned text snippet around EDUCATION:")
    print(re.search(r"education.{0,200}", text_l, re.DOTALL))

    headers = ["education", "academic history", "educational background", "academics"]
    
    # 1. Locate Education Section
    start = None
    for h in headers:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|\n|$)", text_l)
        if m:
            start = m.end()
            print(f"DEBUG: Found header '{h}' at {start}")
            break
            
    if start is None:
        return "None"

    # Stop at next section
    others = [
        "experience", "work experience", "employment", "skills", 
        "projects", "certifications", "achievements", "summary", "awards"
    ]
    end = len(text_l)
    for h in others:
        m = re.search(rf"(?:^|\n)\s*{re.escape(h)}\s*(?::|\n|$)", text_l[start:])
        if m:
            print(f"DEBUG: Found stop header '{h}' at {start + m.start()}")
            end = start + m.start()
            break
            
    section = text_l[start:end]
    print("DEBUG: Extracted Section:\n", section)
    print("--------------------------------------------------")

    # 2. Parse Degree
    if re.search(r"\b(ph\.?d\.?|doctorate|doctor of)\b", section):
        return "PhD"
    
    if re.search(r"\b(master of|master's|masters|m\.?s\.?|m\.?a\.?|m\.?b\.?a\.?|m\.?tech|m\.?eng|ms|ma|mba)\b", section):
        # Find exactly what matched
        m = re.search(r"\b(master of|master's|masters|m\.?s\.?|m\.?a\.?|m\.?b\.?a\.?|m\.?tech|m\.?eng|ms|ma|mba)\b", section)
        print(f"DEBUG: Matched Master with '{m.group(0)}'")
        return "Master"
    
    if re.search(r"\b(bachelor of|bachelor's|bachelors|b\.?s\.?|b\.?a\.?|b\.?tech|b\.?eng|bs|ba)\b", section):
        m = re.search(r"\b(bachelor of|bachelor's|bachelors|b\.?s\.?|b\.?a\.?|b\.?tech|b\.?eng|bs|ba)\b", section)
        print(f"DEBUG: Matched Bachelor with '{m.group(0)}'")
        return "Bachelor"
        
    if re.search(r"\b(associate|a\.?s\.?|a\.?a\.?|as|aa)\b", section):
        return "Associate"

    return "None"

with open("debug_computer-science-major-resume-example.pdf.txt", "r", encoding="utf-8") as f:
    t = f.read()
    print("Result:", extract_education(t))
