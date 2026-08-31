import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { useToast } from "../context/ToastContext.jsx";
import Loader from "../components/Loader.jsx";

function fmtDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function Stat({ label, value, cls }) {
  return (
    <div className={`rounded-2xl p-5 shadow-sm ${cls || "bg-white"}`}>
      <p className="text-xs font-bold uppercase text-slate-400">{label}</p>
      <p className="text-xl font-extrabold mt-1 text-slate-900">₹{value.toLocaleString("en-IN")}</p>
    </div>
  );
}

export default function DriverSalaryPage() {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const BATTA_UNIT = {
    FIXED_TRIP: "₹/trip",
    PER_KM: "₹/km",
    DAILY: "₹/day",
    NONE: "No batta",
  };

  useEffect(() => {
    api
      .get("/api/v1/driver/salary")
      .then(setData)
      .catch((e) => {
        setError(e.message);
        toast.error(e.message);
      });
  }, []);

  const trips = data?.trips || [];
  const totals = data?.totals || { total_batta: 0, total_payable: 0, total_refund: 0 };
  const profile = data?.profile || {};

  return (
    <div className="space-y-4">
      <div>
        <h2 className="page-title">Driver Salary</h2>
        <p className="page-sub">Read-only view of your batta allowance and settlement earnings.</p>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {!data && !error && <Loader label="Loading your salary…" />}

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="Total Driver Salary" value={totals.total_batta || 0} cls="bg-emerald-50" />
            <Stat label="Total Payable to You" value={totals.total_payable || 0} cls="bg-brand-50" />
            <Stat label="Total Refund to Fleet" value={totals.total_refund || 0} cls="bg-amber-50" />
            <StatusStat label="Trips" value={`${trips.length} trips`} />
          </div>
          <div className="card-pad">
            <h3 className="text-sm font-extrabold text-slate-800 mb-1">Batta Profile</h3>
            <p className="text-xs text-slate-500">
              Type: <span className="font-bold text-slate-700">{profile.batta_type || "FIXED_TRIP"}</span>
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Default Rate:{" "}
              <span className="font-bold text-slate-700">
                ₹{(Number(profile.default_batta_rate) || 0).toLocaleString("en-IN")}
              </span>{" "}
              {profile.batta_type === "NONE"
                ? "(no batta)"
                : (BATTA_UNIT[profile.batta_type] || BATTA_UNIT.FIXED_TRIP)}
            </p>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Trip</th>
                  <th>Status</th>
                  <th>Completed</th>
                  <th>Driver Salary</th>
                  <th>Net Due</th>
                </tr>
              </thead>
              <tbody>
                {trips.map((t) => (
                  <tr key={t.trip_code}>
                    <td className="font-semibold text-ink-800">{t.trip_code}</td>
                    <td>{t.status}</td>
                    <td className="text-ink-500">{fmtDate(t.completed_at || t.settled_at)}</td>
                    <td>₹{(t.driver_batta || 0).toLocaleString("en-IN")}</td>
                    <td>
                      ₹{Math.abs(t.net_balance || 0).toLocaleString("en-IN")}
                      {t.net_balance < 0 ? " (to you)" : t.net_balance > 0 ? " (to fleet)" : ""}
                    </td>
                  </tr>
                ))}
                {!trips.length && (
                  <tr>
                    <td colSpan="5" className="empty">
                      No trips assigned yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function StatusStat({ label, value }) {
  return (
    <div className="rounded-2xl p-5 shadow-sm bg-white">
      <p className="text-xs font-bold uppercase text-slate-400">{label}</p>
      <p className="text-xl font-extrabold mt-1 text-slate-900">{value}</p>
    </div>
  );
}