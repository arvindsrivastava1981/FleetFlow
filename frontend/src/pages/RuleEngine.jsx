import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const BADGES = {
  FUEL: "bg-amber-100 text-amber-800",
  TOLL: "bg-rose-100 text-rose-800",
  REPAIR: "bg-orange-100 text-orange-800",
  CHALLAN: "bg-rose-100 text-rose-800",
  DEF: "bg-indigo-100 text-indigo-800",
};

export default function RuleEnginePage() {
  const [rules, setRules] = useState({});
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/v1/rules")
      .then(setRules)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="p-6 bg-white border border-slate-200 rounded-2xl shadow-sm">
        <p className="text-xs text-rose-600 font-semibold">{error}</p>
      </div>
    );
  }

  const entries = Object.entries(rules || {});

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-extrabold text-slate-900">Rule Engine</h2>
        <p className="text-xs text-slate-500">
          Automated checks applied to every expense claim, grouped by expense type.
        </p>
      </div>
      {entries.length === 0 && (
        <p className="text-xs text-slate-400">Loading rules…</p>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {entries.map(([type, items]) => (
          <div
            key={type}
            className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm"
          >
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                BADGES[type] || "bg-slate-100 text-slate-700"
              }`}
            >
              {type}
            </span>
            <ul className="list-disc list-inside mt-3 space-y-1.5">
              {items.map((rule, idx) => (
                <li key={idx} className="text-xs text-slate-600 leading-relaxed">
                  {rule}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}