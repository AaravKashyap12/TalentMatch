from ml.matcher import extract_experience

sample_text_1 = """
Experience
Software Engineer
Google
Jan 2020 - Present
"""

sample_text_2 = """
Work Experience
Frontend Developer
Facebook
2018 - 2020
"""

sample_text_3 = """
Experience
Data Analyst
Amazon
06/2015 - 08/2017
"""

print("Sample 1 (Jan 2020 - Present):", extract_experience(sample_text_1))
print("Sample 2 (2018 - 2020):", extract_experience(sample_text_2))
print("Sample 3 (06/2015 - 08/2017):", extract_experience(sample_text_3))
