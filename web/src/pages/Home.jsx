import { useState } from "react";

import Sidebar from "../components/Sidebar";
import ResultsChart from "../components/ResultsChart";
import ResultsTable from "../components/ResultsTable";
import { scanResumes } from "../api";

// --- Sub-components ---

function Metric({ label, value, subtext }) {
  return (
    <div className="bg-white border border-slate-200 p-6 flex flex-col justify-between h-full shadow-sm hover:shadow-md transition-shadow">
      <div className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">
        {label}
      </div>
      <div className="flex items-end justify-between">
        <div className="text-3xl font-bold text-slate-900">{value}</div>
        {subtext && (
          <div className="text-xs text-slate-400 mb-1">{subtext}</div>
        )}
      </div>
    </div>
  );
}

function Metrics({ results }) {
  if (!results || results.length === 0) return null;

  const scores = results.map((r) => r.final_score);
  const ats = results.map((r) => r.ats_score);
  const avg = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <Metric
        label="Top Match"
        value={`${Math.max(...scores)}%`}
        subtext="Best Candidate"
      />
      <Metric
        label="Average Match"
        value={`${avg(scores).toFixed(1)}%`}
        subtext="Cohort Mean"
      />
      <Metric
        label="Candidates"
        value={results.length}
        subtext="Total Parsed"
      />
      <Metric
        label="Avg ATS Score"
        value={`${avg(ats).toFixed(1)}%`}
        subtext="Keyword Match"
      />
    </div>
  );
}

function WelcomeState() {
  return (
    <div className="h-full flex flex-col justify-center items-center max-w-2xl mx-auto text-center space-y-8 py-12">
      <div className="space-y-2">
        <h2 className="text-3xl font-bold text-slate-900">
          Ready to find your next hire?
        </h2>
        <p className="text-slate-500 text-lg">
          TalentMatch uses intelligent parsing to rank candidates based on
          context, not just keywords.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-left">
        {[
          {
            step: 1,
            title: "Define Role",
            text: "Paste your JD to set the context for the AI ranking engine.",
          },
          {
            step: 2,
            title: "Upload CVs",
            text: "Bulk upload PDF resumes. We handle the parsing automatically.",
          },
          {
            step: 3,
            title: "Analyze",
            text: "Get instant visual rankings and deep-dive analytics.",
          },
        ].map(({ step, title, text }) => (
          <div
            key={step}
            className="p-5 bg-white border border-slate-200 shadow-sm"
          >
            <div className="w-8 h-8 bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold mb-3">
              {step}
            </div>
            <h3 className="font-semibold text-slate-900">{title}</h3>
            <p className="text-sm text-slate-500 mt-1">{text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ErrorBanner({ message, onClose }) {
  if (!message) return null;

  return (
    <div className="mb-6 bg-red-50 border-l-4 border-red-500 p-4 flex justify-between items-center">
      <div className="text-red-700 text-sm font-medium">{message}</div>
      <button
        onClick={onClose}
        className="text-red-500 hover:text-red-700 text-sm font-bold"
      >
        DISMISS
      </button>
    </div>
  );
}

// --- Main Component ---

export default function Home() {
  const [jobDescription, setJobDescription] = useState("");
  const [files, setFiles] = useState([]);
  const [priorities, setPriorities] = useState({
    skills: "Medium",
    experience: "Medium",
    education: "Medium",
    relevance: "Medium",
  });
  const [topN, setTopN] = useState(5);

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleAnalyze() {
    setError(null);

    if (!jobDescription.trim()) {
      setError("Please provide a Job Description to begin analysis.");
      return;
    }

    if (files.length === 0) {
      setError("Please upload at least one resume PDF.");
      return;
    }

    setLoading(true);

    try {
      const res = await scanResumes({ jobDescription, files, priorities });

      if (res?.results) {
        setResults(res.results.slice(0, topN));
      } else {
        throw new Error("Invalid response format");
      }
    } catch (err) {
      console.error(err);
      setError(
        "Analysis failed. Please check your connection or file formats and try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  function downloadCSV() {
    if (!results) return;

    const csv =
      "data:text/csv;charset=utf-8," +
      Object.keys(results[0]).join(",") +
      "\n" +
      results.map((r) => Object.values(r).join(",")).join("\n");

    const link = document.createElement("a");
    link.href = encodeURI(csv);
    link.download = "TalentMatch_Report.csv";
    link.click();
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 font-sans">
      <Sidebar
        jobDescription={jobDescription}
        setJobDescription={setJobDescription}
        files={files}
        setFiles={setFiles}
        priorities={priorities}
        setPriorities={setPriorities}
        topN={topN}
        setTopN={setTopN}
        onAnalyze={handleAnalyze}
        loading={loading}
      />

      <main className="flex-1 p-8 overflow-y-auto">
        <div className="max-w-6xl mx-auto h-full flex flex-col">
          <ErrorBanner message={error} onClose={() => setError(null)} />

          {!results ? (
            <WelcomeState />
          ) : (
            <div className="animate-in fade-in duration-500">
              <div className="mb-8 flex items-center justify-between border-b border-slate-200 pb-4">
                <div>
                  <h1 className="text-2xl font-bold text-slate-900">
                    Analysis Report
                  </h1>
                  <p className="text-slate-500 text-sm mt-1">
                    Ranking based on{" "}
                    {
                      Object.entries(priorities).filter(
                        ([, value]) => value !== "Ignore",
                      ).length
                    }{" "}
                    active criteria
                  </p>
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={() => setResults(null)}
                    className="px-4 py-2 text-slate-600 hover:text-slate-900 font-medium text-sm transition-colors"
                  >
                    Reset Search
                  </button>
                  <button
                    onClick={downloadCSV}
                    className="bg-slate-900 hover:bg-slate-800 text-white px-5 py-2 text-sm font-semibold shadow-sm transition-colors"
                  >
                    Export CSV
                  </button>
                </div>
              </div>

              <Metrics results={results} />

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
                <div className="lg:col-span-2">
                  <ResultsTable results={results} />
                </div>
                <div className="lg:col-span-1">
                  <ResultsChart results={results} />
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
