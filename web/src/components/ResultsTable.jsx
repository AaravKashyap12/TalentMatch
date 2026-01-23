import { useMemo, useState } from "react";

export default function ResultsTable({ results }) {
  const [expandedRows, setExpandedRows] = useState({});

  const sortedResults = useMemo(() => {
    return [...results].sort((a, b) => b.final_score - a.final_score);
  }, [results]);

  function toggleRow(key) {
    setExpandedRows((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className="bg-white border border-slate-200 shadow-sm flex flex-col">
      <div className="p-6 border-b border-slate-100">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
          Candidate Rankings
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Sorted by Match Score (highest first)
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1500px] w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider">
              <th className="py-3 px-4 w-16">Rank</th>
              <th className="py-3 px-4 sticky left-0 bg-slate-50 z-20">
                Candidate
              </th>
              <th className="py-3 px-4">Match %</th>
              <th className="py-3 px-4">ATS %</th>
              <th className="py-3 px-4">Skills Match</th>
              <th className="py-3 px-4">Experience</th>
              <th className="py-3 px-4">Matched Skills</th>
              <th className="py-3 px-4">Skills Score</th>
              <th className="py-3 px-4">Exp Score</th>
              <th className="py-3 px-4">Edu Score</th>
              <th className="py-3 px-4">Relevance</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {sortedResults.map((r, index) => {
              const rowKey = r.candidate_id ?? index;
              const isExpanded = expandedRows[rowKey];

              const visibleSkills = isExpanded
                ? r.matched_skills
                : r.matched_skills.slice(0, 4);

              return (
                <tr
                  key={rowKey}
                  className="hover:bg-slate-50 transition-colors"
                >
                  <td className="py-4 px-4">
                    <div
                      className={`w-7 h-7 flex items-center justify-center text-xs font-bold rounded ${index === 0
                          ? "bg-indigo-100 text-indigo-700"
                          : "bg-slate-100 text-slate-600"
                        }`}
                    >
                      {index + 1}
                    </div>
                  </td>

                  <td className="py-4 px-4 sticky left-0 bg-white z-10">
                    <div className="font-semibold text-slate-900 text-sm">
                      {r.filename ?? r.candidate_name ?? `Candidate ${index + 1}`}
                    </div>
                    <div className="text-xs text-slate-400">
                      ATS: {r.ats_score}%
                    </div>
                  </td>

                  <td className="py-4 px-4 font-bold text-slate-900">
                    {r.final_score}%
                  </td>
                  <td className="py-4 px-4 text-sm">{r.ats_score}%</td>
                  <td className="py-4 px-4 text-sm">
                    {r.matched_skills_count}
                  </td>
                  <td className="py-4 px-4 text-sm">{r.experience}</td>

                  <td className="py-4 px-4">
                    <div className="flex flex-wrap gap-1.5">
                      {visibleSkills.map((skill, i) => (
                        <span
                          key={i}
                          className="px-2 py-1 bg-white border border-slate-200 text-xs text-slate-600 font-medium rounded"
                        >
                          {skill}
                        </span>
                      ))}

                      {r.matched_skills.length > 4 && !isExpanded && (
                        <button
                          onClick={() => toggleRow(rowKey)}
                          className="px-2 py-1 bg-slate-100 text-xs text-slate-500 rounded hover:bg-slate-200"
                        >
                          +{r.matched_skills.length - 4} more
                        </button>
                      )}

                      {isExpanded && (
                        <button
                          onClick={() => toggleRow(rowKey)}
                          className="px-2 py-1 bg-slate-100 text-xs text-slate-500 rounded hover:bg-slate-200"
                        >
                          Show less
                        </button>
                      )}
                    </div>
                  </td>

                  <td className="py-4 px-4 text-sm">{r.skills_score}</td>
                  <td className="py-4 px-4 text-sm">{r.exp_score}</td>
                  <td className="py-4 px-4 text-sm">{r.edu_score}</td>
                  <td className="py-4 px-4 text-sm">{r.relevance_score}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
