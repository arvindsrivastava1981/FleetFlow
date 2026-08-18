import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api.js";

export default function TripsPage() {
  const [trips, setTrips] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/v1/trips")
      .then(setTrips)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-extrabold text-slate-900">Trips</h2>
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">
          {error}
        </div>
      )}
      <div className="space-y-3">
        {trips.map((t) => {
          const active = t.status === "ACTIVE";
          return (
            <Link
              key={t.trip_code}
              to={`/trips/${t.trip_code}`}
              className={`block bg-white border ${
                active ? "border-sky-300 ring-2 ring-sky-100" : "border-slate-200"
              } rounded-2xl p-5 shadow-sm hover:shadow-md transition`}
            >
              <div className="flex flex-wrap justify-between gap-3 items-start">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-extrabold text-slate-900">{t.trip_code}</h3>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        active
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {t.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {t.vehicle_no} · {t.driver_name}
                  </p>
                </div>
                {t.stats && (
                  <div className="text-right">
                    <p className="text-sm font-extrabold text-slate-800">
                      ₹{(t.stats.total_approved || 0).toLocaleString("en-IN")}
                    </p>
                    <p className="text-[10px] text-slate-400">
                      {t.stats.expense_count || 0} expenses
                    </p>
                  </div>
                )}
              </div>
            </Link>
          );
        })}
        {!trips.length && !error && (
          <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center text-sm text-slate-400">
            No trips yet.
          </div>
        )}
      </div>
    </div>
  );
}