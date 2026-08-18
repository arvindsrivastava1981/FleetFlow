import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

export default function DriversPage() {
  const [drivers, setDrivers] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/v1/drivers")
      .then(setDrivers)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-extrabold text-slate-900">Drivers</h2>
        <p className="text-xs text-slate-500">Registered driver users and their batta profile.</p>
      </div>
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">
          {error}
        </div>
      )}
      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Username</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Name</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Batta Type</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Batta Rate</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Phone</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody>
            {drivers.map((d) => (
              <tr key={d.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-3 text-xs font-bold text-slate-800">{d.username}</td>
                <td className="p-3 text-xs text-slate-600">{d.full_name}</td>
                <td className="p-3 text-xs text-slate-600">
                  {d.batta_type === "NONE" ? (
                    <span className="text-slate-400">—</span>
                  ) : (
                    d.batta_type || "FIXED_TRIP"
                  )}
                </td>
                <td className={`p-3 text-xs font-semibold ${d.batta_type === "NONE" ? "text-slate-400" : "text-emerald-700"}`}>
                  {d.batta_type === "NONE"
                    ? "—"
                    : `₹${(Number(d.default_batta_rate) || 0).toLocaleString("en-IN")}`}
                </td>
                <td className="p-3 text-xs text-slate-600">{d.phone || "—"}</td>
                <td className="p-3 text-xs">
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      d.is_active
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-rose-100 text-rose-800"
                    }`}
                  >
                    {d.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
              </tr>
            ))}
            {!drivers.length && (
              <tr>
                <td colSpan="6" className="p-6 text-center text-xs text-slate-400">
                  No drivers yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}