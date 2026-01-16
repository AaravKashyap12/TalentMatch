# TalentMatch 🎯
### Elevating Tech Recruitment with Data-Driven Intelligence

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B)
![NLP](https://img.shields.io/badge/NLP-spaCy-09A3D5)

🚀 **Live Demo**  
👉 https://talentmatch-app.streamlit.app/

---

**TalentMatch** is an advanced, **NLP-driven CV Scanner and ranking system** designed specifically for **Computer Science and Engineering recruitment**.

Unlike generic keyword-based ATS tools, TalentMatch understands **technical context**, extracts **real experience**, and allows recruiters to **dynamically prioritize** what matters most for a role (e.g. Skills > Education for senior positions).

---

## 🚀 Key Features

### 🧠 Intelligent Parsing
- **Universal CS Role Support**: Software Engineering, Data Science, DevOps, Cybersecurity, QA, Research
- **Section-Aware Extraction**: Correctly distinguishes *Experience*, *Projects*, and *Hobbies*
- **Natural Date Understanding**: Handles formats like  
  `"Jan 2020 – Present"`, `"2018–2022"`, `"five years experience"`

### ⚖️ Weighted Ranking Engine
- **Recruiter-Controlled Weights**:
  - 🧠 Skills Match
  - 📅 Experience
  - 🎓 Education
  - 📝 Semantic Content Similarity
- **Normalized Scoring**: Final match score (0–100%) remains balanced regardless of weight configuration

### 👁️ Instant Resume Preview
- Click a candidate to **preview the original PDF**
- No downloads required — faster screening

### 📊 Visual Analytics
- Interactive Plotly charts
- ATS-style insights and cohort statistics
- CSV export for offline analysis

---

## 🛠️ Installation & Setup (Local)

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/AaravKashyap12/TalentMatch.git
cd TalentMatch
