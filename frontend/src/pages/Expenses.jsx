import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { useToast } from "../context/ToastContext.jsx";
import Loader from "../components/Loader.jsx";

function StatusBadge({ status }) {
  if (status === "APPROVED") return <span className="badge badge-success">APPROVED</span>;
  if (status === "REJECTED") return <span className="badge badge-danger">REJECTED</span>;
  return <span className="badge badge-warning">PENDING</span>;
}

export default function ExpensesPage() {
  const toast = useToast();
  const [trips, setTrips] = useState([]);
  const [selected, setSelected] = useState("");
  const [expenses, setExpenses] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/api/v1/trips")
      .then((t) => setTrips(t))
      .catch((e) => {
        setError(e.message);
        toast.error(e.message);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) {
      setExpenses([]);
      return;
    }
    api
      .get(`/api/v1/trips/${selected}`)
      .then((d) =>
        setExpenses(d.expenses || [])
      )
      .catch((e) => {
        setError(e.message);
        toast.error(e.message);
      });
  }, [selected]);

  return (
    <div className="space-y-5">
      <div>
        <h2 className="page-title">Expense Ledger</h2>
        <p className="page-sub">
          Select a trip to review its cleared and flagged expenses.
        </p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <Loader label="Loading trips…" />
      ) : (
      <div className="card-pad">
        <label className="label">Select Trip</label>
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="input md:w-1/2"
        >
          <option value="">— Choose a trip —</option>
          {trips.map((t) => (
            <option key={t.trip_code} value={t.trip_code}>
              {t.trip_code} · {t.vehicle_no}
            </option>
          ))}
        </select>
      </div>
      )}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Flagged</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((e) => (
              <tr key={e.id}>
                <td className="font-semibold text-ink-800">{e.exp_type}</td>
                <td>
                  ₹{(Number(e.amount) || 0).toLocaleString("en-IN")}
                </td>
                <td>
                  <StatusBadge status={e.manager_status} />
                </td>
                <td>
                  {e.is_flagged ? (
                    <span className="badge badge-danger">⚠️ Yes</span>
                  ) : (
                    <span className="text-ink-300">No</span>
                  )}
                </td>
              </tr>
            ))}
            {!expenses.length && selected && (
              <tr>
                <td colSpan="4" className="empty">
                  No expenses on this trip.
                </td>
              </tr>
            )}
            {!expenses.length && !selected && (
              <tr>
                <td colSpan="4" className="empty">
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