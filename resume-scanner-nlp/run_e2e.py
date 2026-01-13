import os
from resume_parser import extract_text_from_pdf
from nlp_utils import clean_text
from matcher import calculate_similarity, extract_skills, extract_experience, calculate_ats_score
import pandas as pd

BASE_DIR = os.path.dirname(__file__)
SAMPLE_DIR = os.path.join(BASE_DIR, 'data', 'sample_resumes')
FILES = [os.path.join(SAMPLE_DIR, f) for f in os.listdir(SAMPLE_DIR) if f.lower().endswith('.pdf')]

job_description = '''We are seeking a Python Developer with experience in AWS, Django, REST APIs and data processing. 3+ years of backend development experience.'''

cleaned_jd = clean_text(job_description)
jd_skills = set(extract_skills(job_description))

results = []
files_content = []

for path in FILES:
    with open(path, 'rb') as f:
        text = extract_text_from_pdf(f)
    cleaned_text = clean_text(text)
    files_content.append(cleaned_text)

    resume_skills = set(extract_skills(text))
    common_skills = jd_skills.intersection(resume_skills)
    experience = extract_experience(text)
    ats = calculate_ats_score(cleaned_text, job_keywords=jd_skills)

    results.append({
        'Candidate Name': os.path.basename(path),
        'Match Score (%)': None,  # filled later
        'ATS Score (%)': round(ats, 2),
        'Matched Skills': ', '.join(list(common_skills)) if common_skills else 'None'
    })

scores = calculate_similarity(cleaned_jd, files_content)
for i, score in enumerate(scores):
    results[i]['Match Score (%)'] = round(score*100, 2)

print(pd.DataFrame(results))
