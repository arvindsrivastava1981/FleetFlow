import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import Loader from "../components/Loader.jsx";

export default function TripsPage() {
  const { user } = useAuth();
  const toast = useToast();
  const [trips, setTrips] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/api/v1/trips")
      .then(setTrips)
      .catch((e) => {
        setError(e.message);
        toast.error(e.message);
      })
      .finally(() => setLoading(false));
  }, []);

  const canCreate =
    user?.role === "trip_manager" || user?.role === "super_admin";

  return (
    <div className="space-y-5">
      <div className="page-head">
        <div>
          <h2 className="page-title">Active Trips</h2>
          <p className="page-sub">All your dispatch trips and their live spend.</p>
        </div>
        {canCreate && (
          <Link to="/trips/new" className="btn-primary">
            + Add New Trip
          </Link>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <Loader label="Loading trips…" />
      ) : (
      <div className="space-y-3">
        {trips.map((t) => {
          const active = t.status === "ACTIVE";
          return (
            <Link
              key={t.trip_code}
              to={`/trips/${t.trip_code}`}
              className={`card card-hover block p-5 ${
                active ? "border-brand-200 ring-1 ring-brand-100" : ""
              }`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-ink-900">{t.trip_code}</h3>
                    <span
                      className={`badge ${
                        active ? "badge-success" : "badge-neutral"
                      }`}
                    >
                      {t.status}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-ink-500">
                    {t.vehicle_no} · {t.driver_name}
                  </p>
                </div>
                {t.stats && (
                  <div className="text-right">
                    <p className="font-extrabold text-ink-900">
                      ₹{(t.stats.total_approved || 0).toLocaleString("en-IN")}
                    </p>
                    <p className="text-xs text-ink-400">
                      {t.stats.expense_count || 0} expenses
                    </p>
                  </div>
                )}
              </div>
            </Link>
          );
        })}
        {!trips.length && !error && (
          <div className="empty card">
            <p className="text-3xl">🚚</p>
            <p className="mt-2 font-medium text-ink-500">No trips yet.</p>            
          </div>
        )}
      </div>
      )}
    </div>
  );
}