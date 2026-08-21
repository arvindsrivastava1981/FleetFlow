import { useEffect, useState } from "react";
import { api } from "../../lib/api.js";
import { useToast } from "../../context/ToastContext.jsx";
import Loader from "../../components/Loader.jsx";

const RULE_BADGES = {
  FUEL: "badge-warning",
  TOLL: "badge-danger",
  REPAIR: "bg-orange-100 text-orange-800",
  CHALLAN: "badge-danger",
  DEF: "badge-brand",
};

function timeAgo(value) {
  if (!value) return "—";
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return value;
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 60) return `${seconds} sec ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export default function BenchmarksPage() {
  const toast = useToast();
  const [benchmarks, setBenchmarks] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [rules, setRules] = useState({});

  function load() {
    api
      .get("/api/v1/benchmarks")
      .then(setBenchmarks)
      .catch((e) => {
        setError(e.message);
        toast.error(e.message);
      })
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  useEffect(() => {
    api
      .get("/api/v1/rules")
      .then(setRules)
      .catch(() => setRules({}));
  }, []);

  async function syncLive() {
    setSyncing(true);
    setError("");
    try {
      await api.post("/api/v1/benchmarks/sync-live", {});
      toast.success("Live rates synced.");
      load();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="page-title">Rules &amp; Rates</h2>
      <p className="page-sub">
        State fuel benchmarks and the automated expense rules.
      </p>
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      <div className="card-pad flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-extrabold text-slate-800">
            Live State Rates
          </h3>
          <p className="text-[11px] text-slate-500 mt-1">
            Pull today's state-level diesel prices into the benchmarks. Falls
            back to a maintained snapshot if the live source is unavailable.
          </p>
        </div>
        <button
          type="button"
          onClick={syncLive}
          disabled={syncing}
          className="btn-primary py-2 px-4 rounded-xl transition shadow disabled:opacity-50"
        >
          {syncing ? "Fetching…" : "Fetch Live Rates"}
        </button>
      </div>

      {loading ? (
        <Loader label="Loading benchmarks…" />
      ) : (
      <div className="table-wrap">
        <table className="table">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Code</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">State</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Price</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Tolerance</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Effective</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Updated</th>
            </tr>
          </thead>
          <tbody>
            {benchmarks.map((b) => (
              <tr key={b.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-3 text-xs font-bold text-slate-800">{b.state_code}</td>
                <td className="p-3 text-xs text-slate-600">{b.state_name}</td>
                <td className="p-3 text-xs text-slate-600">₹{b.benchmark_price_per_liter}</td>
                <td className="p-3 text-xs text-slate-600">{b.tolerance_pct}%</td>
                <td className="p-3 text-xs text-slate-600">
                  {b.effective_date ? new Date(b.effective_date).toLocaleDateString() : "—"}
                </td>
                <td className="p-3 text-xs text-slate-600" title={b.updated_at ? new Date(b.updated_at).toLocaleString() : ""}>
                  {timeAgo(b.updated_at)}
                </td>
              </tr>
            ))}
            {!benchmarks.length && (
              <tr>
                <td colSpan="6" className="p-6 text-center text-xs text-slate-400">No benchmarks yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      )}

      {Object.keys(rules).length > 0 && (
        <div className="space-y-3">
          <div>
            <h3 className="text-sm font-extrabold text-slate-800">
              Expense Rule Engine
            </h3>
            <p className="text-[11px] text-slate-500 mt-1">
              Automated checks applied to every expense claim, grouped by expense type.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Object.entries(rules).map(([type, items]) => (
              <div key={type} className="card-pad">
                <span className={`badge ${RULE_BADGES[type] || "badge-neutral"}`}>
                  {type}
                </span>
                <ul className="mt-3 list-inside list-disc space-y-1.5">
                  {items.map((rule, idx) => (
                    <li key={idx} className="text-sm leading-relaxed text-slate-600">
                      {rule}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}