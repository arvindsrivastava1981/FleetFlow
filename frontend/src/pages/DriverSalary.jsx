import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

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
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/v1/driver/salary")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  const trips = data?.trips || [];
  const totals = data?.totals || { total_batta: 0, total_payable: 0, total_refund: 0 };
  const profile = data?.profile || {};

  return (
    <div className="space-y-4">
      <div>
        <h2 className="page-title">Driver Salary</h2>
        <p className="text-xs text-slate-500">
          Read-only view of your batta allowance and settlement earnings.
        </p>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {!data && !error && (
        <div className="empty card">
          Loading your salary…
        </div>
      )}

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
              / trip
            </p>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Trip</th>
                  <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Status</th>
                  <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Completed</th>
                  <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Driver Salary</th>
                  <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Net Due</th>
                </tr>
              </thead>
              <tbody>
                {trips.map((t) => (
                  <tr key={t.trip_code} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="p-3 text-xs font-bold text-slate-800">{t.trip_code}</td>
                    <td className="p-3 text-xs text-slate-600">{t.status}</td>
                    <td className="p-3 text-xs text-slate-500">{fmtDate(t.completed_at || t.settled_at)}</td>
                    <td className="p-3 text-xs text-slate-700">₹{(t.driver_batta || 0).toLocaleString("en-IN")}</td>
                    <td className="p-3 text-xs text-slate-700">
                      ₹{Math.abs(t.net_balance || 0).toLocaleString("en-IN")}
                      {t.net_balance < 0 ? " (to you)" : t.net_balance > 0 ? " (to fleet)" : ""}
                    </td>
                  </tr>
                ))}
                {!trips.length && (
                  <tr>
                    <td colSpan="5" className="p-6 text-center text-xs text-slate-400">
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