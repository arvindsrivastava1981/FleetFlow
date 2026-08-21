import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { useToast } from "../context/ToastContext.jsx";
import Loader from "../components/Loader.jsx";

function fmtDate(value) {
  if (!value) return "date unavailable";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function SettledTripsPage() {
  const toast = useToast();
  const [trips, setTrips] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/api/v1/settlements")
      .then(setTrips)
      .catch((e) => {
        setError(e.message);
        toast.error(e.message);
      })
      .finally(() => setLoading(false));
  }, []);

  const pdfUrl = (tripCode) =>
    `/api/v1/settlements/${encodeURIComponent(tripCode)}/pdf`;

  const [opening, setOpening] = useState("");

  // The server requires the Bearer token, which a plain <a target="_blank">
  // navigation (cookies only) would not send and would return 401. Fetch the PDF
  // as a blob through the authenticated api layer, then open it in a new tab.
  async function openPdf(tripCode) {
    setOpening(tripCode);
    setError("");
    try {
      const blob = await api.blob(pdfUrl(tripCode));
      const objectUrl = URL.createObjectURL(blob);
      window.open(objectUrl, "_blank", "noopener,noreferrer");
      // Release the object URL reference once the new tab resolves it.
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    } catch (e) {
      setError(e.message);
      toast.error(e.message);
    } finally {
      setOpening("");
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="page-title">Settled Trips</h2>
        <p className="page-sub">
          Open settlement reconciliation PDFs for completed trips.
        </p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {loading ? (
        <Loader label="Loading settled trips…" />
      ) : (
      <div className="space-y-3">
        {trips.map((t) => (
          <div
            key={t.trip_code}
            className="card card-hover flex flex-wrap items-center justify-between gap-4 p-5"
          >
            <div>
              <h3 className="font-bold text-ink-900">{t.trip_code}</h3>
              <p className="mt-1 text-sm text-ink-500">
                {t.vehicle_no} · {t.driver_name}
              </p>
              <p className="mt-1 text-xs text-ink-400">
                Settled {fmtDate(t.settled_at)}
              </p>
            </div>
            <button
              type="button"
              onClick={() => openPdf(t.trip_code)}
              disabled={opening === t.trip_code}
              className="btn-secondary btn-sm"
            >
              {opening === t.trip_code ? "Opening…" : "📄 View Settlement PDF"}
            </button>
          </div>
        ))}
        {!trips.length && !error && (
          <div className="empty card">
            <p className="text-3xl">📑</p>
            <p className="mt-2 font-medium text-ink-500">No settled trips yet.</p>
          </div>
        )}
      </div>
      )}
    </div>
  );
}