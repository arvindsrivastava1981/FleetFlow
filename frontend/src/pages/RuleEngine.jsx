import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

const BADGES = {
  FUEL: "badge-warning",
  TOLL: "badge-danger",
  REPAIR: "bg-orange-100 text-orange-800",
  CHALLAN: "badge-danger",
  DEF: "badge-brand",
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
      <div className="card-pad">
        <p className="text-sm text-rose-700">{error}</p>
      </div>
    );
  }

  const entries = Object.entries(rules || {});

  return (
    <div className="space-y-5">
      <div>
        <h2 className="page-title">Rule Engine</h2>
        <p className="page-sub">
          Automated checks applied to every expense claim, grouped by expense type.
        </p>
      </div>
      {entries.length === 0 && (
        <div className="empty card">
          <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-ink-200 border-t-brand-600" />
          <p className="mt-3">Loading rules…</p>
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {entries.map(([type, items]) => (
          <div key={type} className="card-pad">
            <span className={`badge ${BADGES[type] || "badge-neutral"}`}>
              {type}
            </span>
            <ul className="mt-3 list-inside list-disc space-y-1.5">
              {items.map((rule, idx) => (
                <li key={idx} className="text-sm leading-relaxed text-ink-600">
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