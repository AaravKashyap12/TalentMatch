import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";

export default function ResultsChart({ results, priorities }) {
  if (!results || results.length === 0) {
    return null;
  }

  // Map priorities to weights (Must match backend api/constants.py)
  const PRIORITY_MAP = {
    "Ignore": 0.0,
    "Low": 0.25,
    "Medium": 0.5,
    "High": 0.75,
    "Critical": 1.0,
  };

  const weights = {
    skills: PRIORITY_MAP[priorities?.skills || "Medium"],
    exp: PRIORITY_MAP[priorities?.experience || "Medium"],
    edu: PRIORITY_MAP[priorities?.education || "Medium"],
    rel: PRIORITY_MAP[priorities?.relevance || "Medium"],
  };

  const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0) || 1;

  // 1. Sort by score descending (Show ALL candidates, no slice)
  const topCandidates = [...results]
    .sort((a, b) => b.final_score - a.final_score);

  const formatName = (name) => {
    if (!name) return "Unknown";
    const maxLength = 15;
    return name.length > maxLength ? name.substring(0, maxLength) + "..." : name;
  };

  const data = topCandidates.map((cand) => {
    // Exact Weighted Contribution Calculation
    // Segment Height = (Score * Weight) / TotalWeight
    return {
      name: formatName(cand.filename ?? cand.candidate_name),
      fullName: cand.filename ?? cand.candidate_name,

      Skills: Number(((cand.skills_score * weights.skills) / totalWeight).toFixed(1)),
      Experience: Number(((cand.exp_score * weights.exp) / totalWeight).toFixed(1)),
      Education: Number(((cand.edu_score * weights.edu) / totalWeight).toFixed(1)),
      Relevance: Number(((cand.relevance_score * weights.rel) / totalWeight).toFixed(1)),

      // Keep original for tooltip
      _raw: {
        skills: cand.skills_score,
        exp: cand.exp_score,
        edu: cand.edu_score,
        rel: cand.relevance_score
      }
    };
  });

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      const raw = d._raw || {};
      const totalScore = (d.Skills + d.Experience + d.Education + d.Relevance).toFixed(1);

      return (
        <div className="bg-white border border-slate-200 p-3 rounded shadow-lg text-xs z-50">
          <p className="font-bold text-slate-900 mb-2">{d.fullName}</p>
          <div className="space-y-1">
            <p className="flex justify-between w-40 border-b border-slate-100 pb-1 mb-1">
              <span className="text-slate-900 font-bold">Total Score:</span>
              <span className="font-bold">{totalScore}%</span>
            </p>
            <p className="flex justify-between w-40">
              <span className="text-indigo-600 font-semibold">Skills:</span>
              <span>{raw.skills}%</span>
            </p>
            <p className="flex justify-between">
              <span className="text-emerald-500 font-semibold">Experience:</span>
              <span>{raw.exp}%</span>
            </p>
            <p className="flex justify-between">
              <span className="text-amber-500 font-semibold">Education:</span>
              <span>{raw.edu}%</span>
            </p>
            <p className="flex justify-between">
              <span className="text-rose-500 font-semibold">Relevance:</span>
              <span>{raw.rel}%</span>
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white border border-slate-200 h-full p-6 flex flex-col shadow-sm">
      <div className="mb-2">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
          Detailed Score Breakdown
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Stacked analysis of key metrics
        </p>
      </div>

      <div className="flex-1 min-h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{
              top: 20,
              right: 20,
              left: 0,
              bottom: 100, // Increased to fully clear rotated text
            }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="name"
              tick={{ fill: "#64748b", fontSize: 11, fontWeight: 500 }}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
              interval={0}
              angle={-45} // Rotate labels to prevent congestion
              textAnchor="end"
            />
            <YAxis
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              label={{ value: 'Component Score', angle: -90, position: 'insideLeft', style: { fill: '#94a3b8', fontSize: 11 } }}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f8fafc" }} />
            <Legend
              verticalAlign="top"
              align="right"
              wrapperStyle={{ paddingBottom: "20px", fontSize: "12px" }}
            />

            <Bar dataKey="Skills" stackId="a" fill="#4f46e5" radius={[0, 0, 0, 0]} barSize={40} />
            <Bar dataKey="Experience" stackId="a" fill="#10b981" radius={[0, 0, 0, 0]} barSize={40} />
            <Bar dataKey="Education" stackId="a" fill="#f59e0b" radius={[0, 0, 0, 0]} barSize={40} />
            <Bar dataKey="Relevance" stackId="a" fill="#e11d48" radius={[4, 4, 0, 0]} barSize={40} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
