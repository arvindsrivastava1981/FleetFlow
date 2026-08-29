import { useEffect, useState } from "react";
import { api } from "../../lib/api.js";
import Loader from "../../components/Loader.jsx";

function ic(value) {
  return `₹${Number(value || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 0,
  })}`;
}

function Bar({ label, value, max, suffix = "", accent = "bg-brand-500" }) {
  const pct = max > 0 ? Math.max(4, (value / max) * 100) : 4;
  return (
    <div className="flex items-center gap-2">
      <span className="w-32 shrink-0 truncate text-xs font-medium text-ink-600">{label}</span>
      <div className="h-2.5 flex-1 rounded-full bg-ink-100">
        <div className={`h-2.5 rounded-full ${accent}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-24 shrink-0 text-right text-xs font-bold text-ink-700">
        {suffix === "₹/km" ? `${value ?? "—"} ₹/km` : ic(value)}
      </span>
    </div>
  );
}

// Fleet analytics (feature F-4) — read-only aggregates from the ledger.
// Super Admin sees platform-wide data; Trip Manager sees only their own fleet.
export default function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/api/v1/analytics/overview")
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const cMax = Math.max(
    ...(data?.cost_per_km || []).map((r) => r.spend),
    1
  );
  const lMax = Math.max(
    ...(data?.driver_leakage || []).map((r) => r.total),
    1
  );

  return (
    <div className="space-y-5">
      <div>
        <h2 className="page-title">Analytics</h2>
        <p className="page-sub">Fleet performance from the unified expense ledger.</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {loading ? (
        <Loader label="Crunching the ledger…" />
      ) : (
        <>
          {/* Monthly spend */}
          <section className="card p-5">
            <h3 className="text-base font-bold text-ink-900">Monthly Spend (last 6 months)</h3>
            <div className="mt-4 flex h-40 items-end gap-3">
              {(data?.monthly_spend || []).length ? (
                data.monthly_spend.map((m) => {
                  const max = Math.max(...data.monthly_spend.map((x) => x.total), 1);
                  return (
                    <div key={m.month} className="flex flex-1 flex-col items-center gap-1">
                      <span className="text-[10px] font-bold text-ink-600">{ic(m.total)}</span>
                      <div
                        className="w-full rounded-t-lg bg-brand-500 transition-all"
                        style={{ height: `${Math.max(6, (m.total / max) * 120)}px` }}
                        title={`${m.month}: ${ic(m.total)}`}
                      />
                      <span className="text-[10px] text-ink-400">{m.month}</span>
                    </div>
                  );
                })
              ) : (
                <p className="text-xs text-ink-400">No expenses recorded yet.</p>
              )}
            </div>
          </section>

          {/* Cost per km */}
          <section className="card p-5">
            <h3 className="text-base font-bold text-ink-900">Cost per Vehicle (top spend)</h3>
            <p className="mb-3 text-xs text-ink-500">
              ₹ spent ÷ km driven (odometer delta across that vehicle's trips).
            </p>
            <div className="space-y-2.5">
              {(data?.cost_per_km || []).map((r) => (
                <Bar
                  key={r.vehicle_number}
                  label={r.vehicle_number}
                  value={r.spend}
                  max={cMax}
                />
              ))}
              {!(data?.cost_per_km || []).length && (
                <p className="text-xs text-ink-400">No vehicle spend yet.</p>
              )}
            </div>
          </section>

          {/* Driver leakage */}
          <section className="card p-5">
            <h3 className="text-base font-bold text-ink-900">
              🛡️ Driver-wise Leakage Prevented
            </h3>
            <p className="mb-3 text-xs text-ink-500">
              Value of rejected claims per driver — money saved by verification.
            </p>
            <div className="space-y-2.5">
              {(data?.driver_leakage || []).map((r) => (
                <Bar
                  key={r.driver_name}
                  label={r.driver_name}
                  value={r.total}
                  max={lMax}
                  accent="bg-emerald-500"
                />
              ))}
              {!(data?.driver_leakage || []).length && (
                <p className="text-xs text-ink-400">No rejected claims — nothing to show.</p>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
