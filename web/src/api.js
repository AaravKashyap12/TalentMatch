const BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!BASE_URL) {
  throw new Error("VITE_API_BASE_URL is not defined");
}

export async function scanResumes({ jobDescription, files, priorities }) {
  const formData = new FormData();

  formData.append("job_description", jobDescription);
  formData.append("skills_priority", priorities.skills);
  formData.append("experience_priority", priorities.experience);
  formData.append("education_priority", priorities.education);
  formData.append("relevance_priority", priorities.relevance);

  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await fetch(`${BASE_URL}/scan/pdf`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw error;
  }

  return response.json();
}
