import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api.js";

export default function ExpensesPage() {
  const [trips, setTrips] = useState([]);
  const [selected, setSelected] = useState("");
  const [expenses, setExpenses] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/v1/trips")
      .then((t) => setTrips(t))
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selected) {
      setExpenses([]);
      return;
    }
    api
      .get(`/api/v1/trips/${selected}`)
      .then((d) => setExpenses(d.expenses || []))
      .catch((e) => setError(e.message));
  }, [selected]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-extrabold text-slate-900">Expense Ledger</h2>
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">
          {error}
        </div>
      )}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <label className="font-bold text-slate-700 block text-sm mb-2">Select Trip</label>
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="w-full md:w-1/2 border rounded-lg p-2 bg-slate-50 text-sm"
        >
          <option value="">— Choose a trip —</option>
          {trips.map((t) => (
            <option key={t.trip_code} value={t.trip_code}>
              {t.trip_code} · {t.vehicle_no}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Type</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Amount</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Status</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Flagged</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((e) => (
              <tr key={e.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-3 text-xs font-bold text-slate-800">{e.exp_type}</td>
                <td className="p-3 text-xs text-slate-600">₹{e.amount}</td>
                <td className="p-3 text-xs">
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      e.manager_status === "APPROVED"
                        ? "bg-emerald-100 text-emerald-700"
                        : e.manager_status === "REJECTED"
                        ? "bg-rose-100 text-rose-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {e.manager_status}
                  </span>
                </td>
                <td className="p-3 text-xs">
                  {e.is_flagged ? <span className="font-bold text-rose-600">⚠️ Yes</span> : <span className="text-slate-300">No</span>}
                </td>
              </tr>
            ))}
            {!expenses.length && selected && (
              <tr>
                <td colSpan="4" className="p-6 text-center text-xs text-slate-400">
                  No expenses on this trip.
                </td>
              </tr>
            )}
            {!expenses.length && !selected && (
              <tr>
                <td colSpan="4" className="p-6 text-center text-xs text-slate-400">
                  Select a trip to view its ledger.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}