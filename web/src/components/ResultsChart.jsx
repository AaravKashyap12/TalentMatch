import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function CustomTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const { name } = payload[0].payload;
  const value = payload[0].value;

  return (
    <div className="bg-white border border-slate-200 p-3 shadow-md min-w-[120px]">
      <p className="text-xs font-bold text-slate-400 uppercase mb-1">{name}</p>
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 bg-indigo-600" />
        <p className="text-sm font-bold text-slate-900">{value}% Match</p>
      </div>
    </div>
  );
}

export default function ResultsChart({ results }) {
  if (!results || results.length === 0) {
    return null;
  }

  const data = results.map((r, index) => ({
    name: r.candidate_name
      ? r.candidate_name.split(" ")[0]
      : `Cand. ${index + 1}`,
    score: r.final_score,
  }));

  return (
    <div className="bg-white border border-slate-200 h-full p-6 flex flex-col shadow-sm">
      <div className="mb-6">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
          Distribution
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Final match scores comparison
        </p>
      </div>

      <div className="flex-1 min-h-[250px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 10, right: 0, left: -20, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#f1f5f9"
              vertical={false}
            />
            <XAxis
              dataKey="name"
              tick={{ fill: "#64748b", fontSize: 10, fontWeight: 500 }}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
              interval={0}
            />
            <YAxis
              tick={{ fill: "#64748b", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              domain={[0, 100]}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f8fafc" }} />
            <Bar
              dataKey="score"
              fill="#4f46e5"
              activeBar={{ fill: "#4338ca" }}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
