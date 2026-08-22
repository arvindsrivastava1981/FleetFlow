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

// Price movement vs the previously synced rate (previous_price column).
// Returns null when unknown/unchanged so the Change cell shows a quiet dash.
function priceChange(b) {
  const prev = b.previous_price == null ? null : Number(b.previous_price);
  const curr = Number(b.benchmark_price_per_liter);
  if (!prev || Number.isNaN(prev) || prev === curr) return null;
  const delta = curr - prev;
  return { up: delta > 0, delta, pct: (delta / prev) * 100 };
}

export default function BenchmarksPage() {
  const toast = useToast();
  const [benchmarks, setBenchmarks] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [rules, setRules] = useState({});
  const [states, setStates] = useState([]);
  const [homeState, setHomeState] = useState("");
  const [busyCode, setBusyCode] = useState("");

  function load() {
    api
      .get("/api/v1/benchmarks")
      .then((data) => {
        setBenchmarks(data?.benchmarks || []);
        setHomeState(data?.home_state_code || "");
      })
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

  useEffect(() => {
    api
      .get("/api/v1/states")
      .then(setStates)
      .catch(() => setStates([]));
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

  async function toggleFavorite(b) {
    setBusyCode(b.state_code);
    try {
      if (b.is_favorite) {
        await api.del(`/api/v1/benchmarks/${b.state_code}/favorite`);
        toast.success(`${b.state_name} removed from favorites.`);
      } else {
        await api.post(`/api/v1/benchmarks/${b.state_code}/favorite`, {});
        toast.success(`${b.state_name} added to favorites.`);
      }
      setBenchmarks((rows) =>
        rows.map((r) =>
          r.state_code === b.state_code ? { ...r, is_favorite: !b.is_favorite } : r,
        ),
      );
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setBusyCode("");
    }
  }

  async function changeHomeState(e) {
    const code = e.target.value;
    try {
      await api.put("/api/v1/benchmarks/home-state", { state_code: code });
      setHomeState(code);
      toast.success(code ? `Usual state set to ${code}.` : "Usual state cleared.");
    } catch (err) {
      toast.error(err.message);
    }
  }

  // Favorites pin to the top; alphabetical within each group.
  const sortedRows = [...benchmarks].sort(
    (a, b) =>
      Number(b.is_favorite === true) - Number(a.is_favorite === true) ||
      String(a.state_name).localeCompare(String(b.state_name)),
  );

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
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs font-semibold text-slate-600">
            My usual state
            <select
              value={homeState}
              onChange={changeHomeState}
              title="The state where your trips usually happen — its row is highlighted below."
              className="ml-2 rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-700 focus:border-slate-500 focus:outline-none"
            >
              <option value="">— None —</option>
              {states.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.name} ({s.code})
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={syncLive}
            disabled={syncing}
            className="btn-primary py-2 px-4 rounded-xl transition shadow disabled:opacity-50"
          >
            {syncing ? "Fetching…" : "Fetch Live Rates"}
          </button>
        </div>
      </div>

      <div className="card-pad bg-blue-50 border border-blue-200">
        <h3 className="text-sm font-extrabold text-blue-900">What is Tolerance?</h3>
        <p className="mt-1 text-xs leading-relaxed text-blue-800">
          Tolerance is the allowed drift around a state's benchmark diesel price
          before a FUEL claim gets flagged by the rules engine. Example: Uttar
          Pradesh benchmark ₹91.50/L with 8% tolerance → fuel claims between
          ₹84.18 and ₹98.82 per liter pass automatically; anything outside that
          band (e.g. a claim at ₹105/L) is flagged for manager review.
        </p>
      </div>

      {loading ? (
        <Loader label="Loading benchmarks…" />
      ) : (
      <div className="table-wrap">
        <table className="table">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">★</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Code</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">State</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Price</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">
                <span
                  className="relative group cursor-help"
                  title="Allowed drift ±% around the benchmark price before a FUEL claim is flagged."
                >
                  Tolerance ⓘ
                  <span className="pointer-events-none hidden group-hover:block absolute right-0 top-full mt-2 z-20 w-72 rounded-xl bg-slate-800 p-3 text-left text-[11px] font-medium normal-case leading-relaxed text-white shadow-xl">
                    Tolerance sets how far a driver's claimed fuel rate may drift
                    from the benchmark. Example: UP benchmark ₹91.50/L ± 8% →
                    claims of ₹84.18–₹98.82/L pass automatically; outside that
                    band the expense is flagged for manager review.
                  </span>
                </span>
              </th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Change</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Effective</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Updated</th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((b) => {
              const change = priceChange(b);
              const isUsual = Boolean(homeState) && b.state_code === homeState;
              return (
                <tr
                  key={b.id}
                  className={`border-b border-slate-100 ${isUsual ? "bg-emerald-50" : "hover:bg-slate-50"}`}
                >
                  <td className="p-3">
                    <button
                      type="button"
                      disabled={busyCode === b.state_code}
                      onClick={() => toggleFavorite(b)}
                      title={b.is_favorite ? "Remove from favorites" : "Add to favorites"}
                      aria-label={
                        b.is_favorite
                          ? `Remove ${b.state_code} from favorites`
                          : `Add ${b.state_code} to favorites`
                      }
                      className={`text-lg leading-none transition disabled:opacity-40 ${
                        b.is_favorite ? "text-amber-500" : "text-slate-300 hover:text-amber-400"
                      }`}
                    >
                      {b.is_favorite ? "★" : "☆"}
                    </button>
                  </td>
                  <td className="p-3 text-xs font-bold text-slate-800">
                    {b.state_code}
                    {isUsual && (
                      <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-emerald-700">
                        Usual
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-xs text-slate-600">{b.state_name}</td>
                  <td className="p-3 text-xs text-slate-600">₹{b.benchmark_price_per_liter}</td>
                  <td className="p-3 text-xs text-slate-600">{b.tolerance_pct}%</td>
                  <td className="p-3 text-xs whitespace-nowrap">
                    {!change ? (
                      <span className="text-slate-300">—</span>
                    ) : change.up ? (
                      <span className="font-bold text-red-600">
                        ▲ +₹{change.delta.toFixed(2)}{" "}
                        <span className="text-[10px] font-semibold">
                          (+{change.pct.toFixed(2)}%)
                        </span>
                      </span>
                    ) : (
                      <span className="font-bold text-green-600">
                        ▼ −₹{Math.abs(change.delta).toFixed(2)}{" "}
                        <span className="text-[10px] font-semibold">
                          ({change.pct.toFixed(2)}%)
                        </span>
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-xs text-slate-600">
                    {b.effective_date ? new Date(b.effective_date).toLocaleDateString() : "—"}
                  </td>
                  <td className="p-3 text-xs text-slate-600" title={b.updated_at ? new Date(b.updated_at).toLocaleString() : ""}>
                    {timeAgo(b.updated_at)}
                  </td>
                </tr>
              );
            })}
            {!sortedRows.length && (
              <tr>
                <td colSpan="8" className="p-6 text-center text-xs text-slate-400">No benchmarks yet.</td>
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