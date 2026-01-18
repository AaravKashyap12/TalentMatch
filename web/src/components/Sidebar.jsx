const PRIORITY_OPTIONS = ["Ignore", "Low", "Medium", "High", "Critical"];

export default function Sidebar({
  jobDescription,
  setJobDescription,
  files,
  setFiles,
  priorities,
  setPriorities,
  topN,
  setTopN,
  onAnalyze,
  loading,
}) {
  function handleFileChange(e) {
    const selectedFiles = Array.from(e.target.files);

    setFiles((prev) => {
      const existingNames = new Set(prev.map((f) => f.name));
      return [
        ...prev,
        ...selectedFiles.filter((f) => !existingNames.has(f.name)),
      ];
    });

    e.target.value = "";
  }

  return (
    <aside className="w-80 bg-white border-r border-slate-200 flex flex-col h-full shadow-[4px_0_24px_rgba(0,0,0,0.02)] z-10">
      <div className="p-6 border-b border-slate-100">
        <h2 className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <span className="w-2 h-6 bg-indigo-600 inline-block" />
          TalentMatch
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
        <div className="space-y-3">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Job Context
          </label>
          <textarea
            className="w-full bg-slate-50 text-slate-900 p-3 text-sm min-h-[120px] border border-slate-200 focus:border-indigo-600 focus:ring-0 transition-colors placeholder:text-slate-400"
            placeholder="Paste JD here (e.g., 'Senior React Developer with 5 years exp...')"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
          />
        </div>

        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Resumes
            </label>
            {files.length > 0 && (
              <span className="bg-slate-100 text-slate-600 text-[10px] font-bold px-2 py-0.5 rounded-full">
                {files.length} READY
              </span>
            )}
          </div>

          <input
            id="resume-upload"
            type="file"
            accept="application/pdf"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />

          <label
            htmlFor="resume-upload"
            className="group cursor-pointer flex flex-col items-center justify-center border border-slate-300 border-dashed bg-slate-50 p-6 hover:bg-slate-100 hover:border-slate-400 transition-all"
          >
            <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900">
              Upload PDFs
            </span>
          </label>

          {files.length > 0 && (
            <div className="mt-2 space-y-1">
              <div className="flex justify-between text-xs text-slate-400 mb-2">
                <span>Selected files:</span>
                <button
                  onClick={() => setFiles([])}
                  className="text-red-500 hover:text-red-700 font-medium"
                >
                  Clear All
                </button>
              </div>

              <div className="max-h-32 overflow-y-auto pr-1 space-y-1">
                {files.map((file, index) => (
                  <div
                    key={index}
                    className="text-xs text-slate-600 bg-slate-50 px-2 py-1.5 border border-slate-100 truncate"
                  >
                    {file.name}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Ranking Weights
          </label>

          <div className="grid grid-cols-1 gap-3">
            {[
              ["skills", "Skills Match"],
              ["experience", "Yrs Experience"],
              ["education", "Education"],
              ["relevance", "Semantic Match"],
            ].map(([key, label]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-sm text-slate-600">{label}</span>
                <select
                  value={priorities[key]}
                  onChange={(e) =>
                    setPriorities((prev) => ({
                      ...prev,
                      [key]: e.target.value,
                    }))
                  }
                  className="text-xs font-medium bg-white border border-slate-200 text-slate-900 py-1 px-2 focus:border-indigo-600 focus:outline-none cursor-pointer w-24"
                >
                  {PRIORITY_OPTIONS.map((opt) => (
                    <option key={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              Top Candidates
            </label>
            <span className="text-xs font-bold text-indigo-600">{topN}</span>
          </div>

          <input
            type="range"
            min={1}
            max={20}
            value={topN}
            onChange={(e) => setTopN(Number(e.target.value))}
            className="w-full h-1 bg-slate-200 appearance-none cursor-pointer accent-indigo-600"
          />
        </div>
      </div>

      <div className="p-6 border-t border-slate-100 bg-slate-50">
        <button
          onClick={onAnalyze}
          disabled={loading}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-4 shadow-sm disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors text-sm"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Processing...
            </span>
          ) : (
            "Analyze Resumes"
          )}
        </button>
      </div>
    </aside>
  );
}
