const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
const API_KEY = import.meta.env.VITE_TM_API_KEY;

if (!API_KEY && import.meta.env.PROD) {
  console.warn("TalentMatch: VITE_TM_API_KEY is missing. API calls will fail.");
}

export async function scanResumes({ jobDescription, files, priorities }) {
  const formData = new FormData();

  formData.append("job_description", jobDescription);
  formData.append("required_skills", "[]");
  formData.append("preferred_skills", "[]");
  formData.append("min_years_experience", "null");
  formData.append("required_degree", "null");
  formData.append("skills_priority", priorities.skills);
  formData.append("experience_priority", priorities.experience);
  formData.append("education_priority", priorities.education);
  formData.append("relevance_priority", priorities.relevance);

  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(`${BASE_URL}/scan/pdf`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw error;
  }

  return response.json();
}