import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

function fmtDate(value) {
  if (!value) return "date unavailable";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export default function ReportsPage() {
  const [trips, setTrips] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/v1/settlements")
      .then(setTrips)
      .catch((e) => setError(e.message));
  }, []);

  const pdfUrl = (tripCode) => `/api/v1/settlements/${encodeURIComponent(tripCode)}/pdf`;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-extrabold text-slate-900">Final Reports</h2>
        <p className="text-xs text-slate-500">
          View settlement reconciliation PDFs for your settled trips.
        </p>
      </div>
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">
          {error}
        </div>
      )}
      <div className="space-y-3">
        {trips.map((t) => (
          <div
            key={t.trip_code}
            className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4"
          >
            <div>
              <h3 className="font-extrabold text-slate-900">{t.trip_code}</h3>
              <p className="text-xs text-slate-500 mt-1">
                {t.vehicle_no} · {t.driver_name}
              </p>
              <p className="text-[11px] text-slate-400 mt-2">
                Settled {fmtDate(t.settled_at)}
              </p>
            </div>
            <a
              href={pdfUrl(t.trip_code)}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-sky-600 hover:bg-sky-500 text-white font-bold px-4 py-2.5 rounded-xl text-xs transition shadow flex items-center gap-1.5"
            >
              📄 View Settlement PDF
            </a>
          </div>
        ))}
        {!trips.length && !error && (
          <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center text-sm text-slate-400">
            No settled trips yet.
          </div>
        )}
      </div>
    </div>
  );
}