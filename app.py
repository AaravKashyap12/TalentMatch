import streamlit as st
import spacy

st.set_page_config(
    page_title="TalentMatch",
    page_icon="🎯",
    layout="wide"
)

@st.cache_resource
def load_nlp():
    return spacy.load("en_core_web_sm")

nlp = load_nlp()



import pandas as pd
import plotly.express as px
import base64
from resume_parser import extract_text_from_pdf
from nlp_utils import clean_text
from matcher import calculate_similarity, extract_skills, extract_experience, calculate_ats_score, calculate_component_scores

# Page Configuration

import base64
import streamlit.components.v1 as components

def display_pdf(file):
    file.seek(0)
    base64_pdf = base64.b64encode(file.read()).decode("utf-8")

    pdf_viewer = f"""
    <iframe
        src="https://mozilla.github.io/pdf.js/web/viewer.html?file=data:application/pdf;base64,{base64_pdf}"
        width="100%"
        height="700px"
        style="border: none;"
    ></iframe>
    """

    components.html(pdf_viewer, height=700, scrolling=True)



# Custom Professional CSS (Dark Mode Compatible)
st.markdown("""
    <style>
    /* Global Styles */
    .stApp {
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-weight: 700;
        color: #64B5F6 !important; /* Lighter blue for dark background */
    }
    
    /* Metrics Card - Dark Mode Compatible */
    div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.05); /* Transparent/Glassy */
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Button Styling */
    .stButton>button {
        background-color: #2E86C1;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1B4F72;
        box-shadow: 0 4px 12px rgba(46, 134, 193, 0.4);
        transform: translateY(-2px);
    }
    
    /* File Uploader Customization */
    .stFileUploader {
        padding: 20px;
        border-radius: 10px;
        border: 1px dashed #2E86C1;
    }
    </style>
    """, unsafe_allow_html=True)

# Main Title Area
col1, col2 = st.columns([3, 1])
with col1:
    st.title("TalentMatch 🎯")
    st.markdown("##### Elevating Tech Recruitment with **Data-Driven Intelligence**")
with col2:
    st.info("💡 **Pro Tip**: Intelligent parsing for **Dev, Data, Security, QA, & Cloud** roles.")

st.divider()

# Initialize session state for file uploader key
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0

def clear_files():
    st.session_state["file_uploader_key"] += 1

# Layout: Sidebar for Uploads & Settings
with st.sidebar:
    st.header("📂 Data Input")
    uploaded_files = st.file_uploader(
        "Upload Resumes (PDF)", 
        type=["pdf"], 
        accept_multiple_files=True,
        key=f"uploader_{st.session_state['file_uploader_key']}"
    )
    
    # Show file count
    if uploaded_files:
        st.caption(f"📂 **{len(uploaded_files)}** files selected")

    # Remove All Button
    if uploaded_files:
        if st.button("🗑️ Remove All Files", type="secondary"):
            clear_files()
            st.rerun()
    
    st.markdown("### ⚖️ Ranking Priorities")
    with st.expander("Customize Weights", expanded=True):
        st.info("Adjust the importance of each factor for this role:")
        
        priority_options = ["Ignore", "Low", "Medium", "High", "Critical"]
        priority_map = {"Ignore": 0.0, "Low": 0.25, "Medium": 0.5, "High": 0.75, "Critical": 1.0}
        
        p_skills = st.select_slider("🧠 Skills Match", options=priority_options, value="High")
        p_exp = st.select_slider("📅 Experience", options=priority_options, value="Medium")
        p_edu = st.select_slider("🎓 Education", options=priority_options, value="Low")
        p_rel = st.select_slider("📝 Content Relevance", options=priority_options, value="Low")
        
        # Map to weights
        w_skills = priority_map[p_skills]
        w_exp = priority_map[p_exp]
        w_edu = priority_map[p_edu]
        w_rel = priority_map[p_rel]
        
    st.markdown("### ⚙️ Preferences")
    top_n = st.slider("Max Candidates to Display", 1, 20, 5)
    st.markdown("---")
    st.markdown("---")
    st.markdown("Created with ❤️ by **Aarav**")
    st.caption("© 2026 TalentMatch Intelligence")

# Main Content Area
job_description = st.text_area("📝 Paste Job Description", height=200, placeholder="Enter the job description here to start matching...")

if st.button("🚀 Analyze Candidates", type="primary"):
    if not uploaded_files:
        st.warning("⚠️ Please upload at least one resume PDF.")
    elif not job_description:
        st.warning("⚠️ Please enter a job description.")
    else:
        with st.spinner("🔍 analyzing resumes... keying in weights..."):
            # Core Processing
            cleaned_jd = clean_text(job_description)
            jd_skills = set(extract_skills(job_description))
            
            results = []
            files_content = []      # Cleaned (for TF-IDF)
            raw_files_content = []  # Raw (for Extraction)
            
            for file in uploaded_files:
                text = extract_text_from_pdf(file)
                
                # Store Raw
                raw_files_content.append(text)
                
                # Store Clean
                cleaned_text = clean_text(text)
                files_content.append(cleaned_text)
                
                # ... (rest of local loop uses vars as needed)
                resume_skills = set(extract_skills(text)) # Use Raw locally
                common_skills = jd_skills.intersection(resume_skills)
                experience = extract_experience(text) # Use Raw locally
                
                ats_score = calculate_ats_score(cleaned_text, job_keywords=jd_skills)

                results.append({
                    "Candidate Name": file.name,
                    "Skills Match Count": len(common_skills),
                    "Experience": ", ".join(experience) if experience else "Not detected",
                    "Matched Skills": ", ".join(list(common_skills)) if common_skills else "None",
                    "ATS Score (%)": round(ats_score, 2)
                })

            # Calculate Weighted Scores
            weights = {'skills': w_skills, 'experience': w_exp, 'education': w_edu, 'relevance': w_rel}
            
            # PASS RAW AND CLEAN: (CleanJD, CleanCVs, RawJD, RawCVs, Weights)
            weighted_results = calculate_component_scores(
                cleaned_jd, 
                files_content, 
                job_description, 
                raw_files_content, 
                weights
            )
            
            for i, res in enumerate(weighted_results):
                results[i]["Match Score (%)"] = res['final_score']
                results[i]["Skills Score"] = res['skills_score']
                results[i]["Exp Score"] = res['exp_score']
                results[i]["Edu Score"] = res['edu_score']
                results[i]["Relevance Score"] = res['relevance_score']
            
            # Create DataFrame & Sort
            df = pd.DataFrame(results)
            df = df.sort_values(by="Match Score (%)", ascending=False).reset_index(drop=True)
            df.index += 1
            top_df = df.head(top_n)
            
            # Store in Session State
            st.session_state['analysis_results'] = {
                'df': df,
                'top_df': top_df
            }
            st.rerun()

# Display Results from Session State
if 'analysis_results' in st.session_state:
    data = st.session_state['analysis_results']
    df = data['df']
    top_df = data['top_df']

    # --- Visualizations & Metrics ---
    # Convert uploaded_files to a list if not already (it usually is)
    # Note: If user uploads new files, they won't be processed until 'Analyze' is clicked again.
    
    st.success(f"✅ Analysis Complete!")
    
    # Key Metrics Row
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Top Score", f"{top_df.iloc[0]['Match Score (%)']}%", delta="Best Match")
    with m2:
        st.metric("Avg Score", f"{round(df['Match Score (%)'].mean(), 1)}%")
    with m3:
        st.metric("Total Candidates", len(df))

    # Additional ATS Metrics
    a1, a2, a3 = st.columns(3)
    with a1:
        st.metric("Avg ATS", f"{round(df['ATS Score (%)'].mean(), 1)}%")
    with a2:
        st.metric("Top ATS", f"{round(top_df.iloc[0]['ATS Score (%)'], 1)}%")
    with a3:
        st.metric("ATS Median", f"{round(df['ATS Score (%)'].median(), 1)}%")

    st.markdown("### 📊 Performance Overview")
    
    # Interactive Bar Chart using Plotly
    fig = px.bar(
        top_df, 
        x="Candidate Name", 
        y="Match Score (%)",
        color="Match Score (%)",
        color_continuous_scale="Blues",
        title="Top Ranked Candidates Comparison",
        text="Match Score (%)",
        template="plotly_white"
    )
    fig.update_layout(xaxis_title="", yaxis_title="Relevance Score")
    st.plotly_chart(fig, use_container_width=True)

    # Detailed Data Table
    st.markdown("### 🏆 Detailed Rankings")
    st.caption("👇 **Click on a row** to preview the resume!")
    
    # Enable selection
    selection = st.dataframe(
        top_df.style.background_gradient(subset=["Match Score (%)"], cmap="Blues"),
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    with st.expander("📄 View Full Analysis Data"):
        st.table(df)

    # --- PDF Preview Section ---
    if selection.selection.rows:
        selected_index = selection.selection.rows[0]
        try:
            # Get the Candidate Name from the selected row
            # The rows index is 0-based integer position in the displayed dataframe
            selected_row = top_df.iloc[selected_index] 
            selected_filename = selected_row["Candidate Name"]
            
            st.divider()
            st.markdown(f"### 📄 Preview: {selected_filename}")
            
            # Find the file object
            selected_file = next((f for f in uploaded_files if f.name == selected_filename), None)
            
            if selected_file:
                display_pdf(selected_file)
            else:
                st.error("File not found in memory (try re-uploading if you refreshed the page).")
                
        except Exception as e:
           st.write(f"Selection error: {e}")

    # Download Section
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download Full Report (CSV)",
        csv,
        "TalentMatch_Report.csv",
        "text/csv",
        key='download-csv'
    )
