import React from 'react';

export default function CandidateCard({ data }) {
  const verdict = getVerdict(data.score);
  const verdictColor = verdict === "Strong Hire" ? "text-green-600" : verdict === "Consider" ? "text-amber-600" : "text-red-600";
  const verdictBg = verdict === "Strong Hire" ? "bg-green-50" : verdict === "Consider" ? "bg-amber-50" : "bg-red-50";

  return (
    <div className="bg-white shadow-xl rounded-2xl p-6 w-full border border-gray-100 hover:border-blue-200 transition-all">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900">{(data.filename || data.name || 'Candidate').replace(/\.pdf$/i,'').replace(/[-_]/g,' ')}</h2>
          <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mt-1 ${verdictBg} ${verdictColor}`}>
            {verdict}
          </div>
        </div>
        <div className="text-4xl font-extrabold text-blue-600">
          {Math.round(data.score)}%
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <Bar label="Skills" value={data.breakdown.skills} color="bg-blue-500" />
        <Bar label="Experience" value={data.breakdown.experience} color="bg-green-500" />
        <Bar label="Relevance" value={data.breakdown.semantic} color="bg-indigo-500" />
        <Bar label="ATS" value={data.breakdown.ats || 0.7} color="bg-gray-500" />
      </div>

      {data.missing && data.missing.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">Missing Skills</h3>
          <div className="flex flex-wrap gap-2">
            {data.missing.map((s, i) => (
              <span key={i} className="px-2 py-1 bg-red-50 text-red-600 text-xs font-medium rounded-md border border-red-100">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
      
      {data.matched_skills && data.matched_skills.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">Top Matched Skills</h3>
          <div className="flex flex-wrap gap-2">
            {data.matched_skills.slice(0, 5).map((s, i) => (
              <span key={i} className="px-2 py-1 bg-blue-50 text-blue-600 text-xs font-medium rounded-md border border-blue-100">
                {s}
              </span>
            ))}
            {data.matched_skills.length > 5 && (
              <span className="text-xs text-gray-400 self-center">+{data.matched_skills.length - 5} more</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Bar({ label, value, color }) {
  // value is expected to be 0-1
  const pct = Math.min(Math.max(value * 100, 0), 100);
  return (
    <div>
      <div className="flex justify-between text-xs font-medium text-gray-500 mb-1">
        <span>{label}</span>
        <span>{Math.round(pct)}%</span>
      </div>
      <div className="w-full bg-gray-100 h-1.5 rounded-full overflow-hidden">
        <div
          className={`${color} h-full rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function getVerdict(score) {
  if (score > 75) return "Strong Hire";
  if (score > 60) return "Consider";
  return "Reject";
}
