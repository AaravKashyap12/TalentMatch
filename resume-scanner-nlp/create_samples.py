from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

def create_resume_pdf(filename, text):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    text_object = c.beginText(40, height - 40)
    
    for line in text.split('\n'):
        text_object.textLine(line)
        
    c.drawText(text_object)
    c.save()

def main():
    if not os.path.exists("data/sample_resumes"):
        os.makedirs("data/sample_resumes")
        
    resume_1_text = """
    John Doe
    Python Developer
    
    Skills: Python, Django, SQL, AWS, Git, Machine Learning.
    Experience:
    - Senior Python Developer at TechCorp (4 years)
    - Developed backend APIs using Django and PostgreSQL.
    - Deployed models on AWS.
    """
    
    resume_2_text = """
    Jane Smith
    Data Analyst
    
    Skills: SQL, Excel, Tableau, Python, Data Visualization.
    Experience:
    - Data Analyst at DataInc (2 years)
    - Created dashboards in Tableau.
    - Analyzed marketing data using Python (Pandas).
    """

    create_resume_pdf("data/sample_resumes/Resume_John_Python.pdf", resume_1_text)
    create_resume_pdf("data/sample_resumes/Resume_Jane_Analyst.pdf", resume_2_text)

if __name__ == "__main__":
    main()

