import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import Loader from "../components/Loader.jsx";
import { EXPENSE_TYPES, parseBulkRows } from "../lib/expenseUtils.js";
import { enqueue, isNetworkError } from "../lib/offlineQueue.js";

const EMPTY_ROW = { exp_type: "FUEL", amount: "", liters: "", odometer: "", note: "" };

export default function BulkEntryPage() {
  const { tripCode } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const [trip, setTrip] = useState(null);
  const [error, setError] = useState("");
  const [paste, setPaste] = useState("");
  const [rows, setRows] = useState([]);
  const [skipped, setSkipped] = useState([]);
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState(null);

  const canEnter = user?.role === "trip_manager" || user?.role === "super_admin";

  useEffect(() => {
    api
      .get(`/api/v1/trips/${tripCode}`)
      .then((d) => setTrip(d?.trip))
      .catch((e) => setError(e.message));
  }, [tripCode]);

  function importPaste() {
    const { rows: parsed, skipped: bad } = parseBulkRows(paste);
    if (parsed.length) {
      setRows((r) => [...r, ...parsed]);
      toast.success(`Imported ${parsed.length} row${parsed.length > 1 ? "s" : ""}.`);
    }
    setSkipped(bad);
    if (!parsed.length && bad.length) toast.error("Nothing importable — check the format.");
    setPaste("");
  }

  function setRow(i, key, val) {
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, [key]: val } : r)));
  }

  async function saveAll() {
    if (!rows.length) {
      toast.error("Add at least one row first.");
      return;
    }
    setBusy(true);
    setError("");
    setResults(null);
    let saved = 0;
    let queued = 0;
    const failed = [];
    for (const row of rows) {
      const amount = Number(row.amount);
      if (!Number.isFinite(amount) || amount <= 0) {
        failed.push(`${row.exp_type} — invalid amount`);
        continue;
      }
      const payload = {
        trip_code: tripCode,
        exp_type: row.exp_type,
        amount,
        liters: Number(row.liters || 0),
        odometer: Number(row.odometer || 0),
        ...(row.note && row.note.trim()
          ? { raw_receipt_text: row.note.trim() }
          : {}),
      };
      try {
        await api.post("/api/v1/expenses", payload);
        saved += 1;
      } catch (err) {
        if (isNetworkError(err)) {
          enqueue(payload);
          queued += 1;
        } else {
          failed.push(`${row.exp_type} ₹${amount} — ${err.message}`);
        }
      }
    }
    setResults({ saved, queued, failed });
    if (saved) {
      setRows([]);
      toast.success(`Saved ${saved} expense${saved > 1 ? "s" : ""}.`);
    }
    if (queued) toast.info(`${queued} queued offline — will sync when online.`);
    if (failed.length) toast.error(`${failed.length} row${failed.length > 1 ? "s" : ""} failed.`);
    setBusy(false);
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center justify-between">
          <h2 className="page-title">Bulk Entry</h2>
          <Link to={`/trips/${tripCode}`} className="btn-secondary text-sm">
            ← Trip
          </Link>
        </div>
        <p className="page-sub">
          Log many receipts at once for trip <span className="font-bold">{tripCode}</span>.
          {trip && trip.status !== "ACTIVE" && (
            <span className="ml-2 text-amber-600">(trip is {trip.status})</span>
          )}
        </p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {!canEnter ? (
        <div className="alert alert-error">Only managers can log expenses.</div>
      ) : (
        <>
          {/* Paste box */}
          <div className="card p-4">
            <label className="label" htmlFor="bulk-paste">
              Paste from Excel / CSV (one receipt per line: type, amount[, litres, odometer, note])
            </label>
            <textarea
              id="bulk-paste"
              value={paste}
              onChange={(e) => setPaste(e.target.value)}
              rows={4}
              placeholder={"FUEL, 4500, 50, 102000, Pune pump\nTOLL, 320\nREPAIR, 1800"}
              className="input w-full font-mono text-xs"
            />
            <div className="mt-2 flex items-center gap-3">
              <button type="button" onClick={importPaste} disabled={!paste.trim() || busy} className="btn-secondary">
                ⬇ Import rows
              </button>
              <button type="button" onClick={() => setRows((r) => [...r, { ...EMPTY_ROW }])} className="btn-secondary">
                + Add blank row
              </button>
            </div>
            {skipped.length > 0 && (
              <p className="mt-2 text-[11px] text-rose-600">
                Skipped {skipped.length} line{skipped.length > 1 ? "s" : ""}:{" "}
                {skipped.slice(0, 3).map((s) => s.reason).join("; ")}
                {skipped.length > 3 ? "…" : ""}
              </p>
            )}
          </div>

          {/* Rows */}
          {rows.length > 0 && (
            <div className="table-wrap">
              <table className="table">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="p-2 text-[10px] font-bold text-slate-500 uppercase">Type</th>
                    <th className="p-2 text-[10px] font-bold text-slate-500 uppercase">Amount</th>
                    <th className="p-2 text-[10px] font-bold text-slate-500 uppercase">Litres</th>
                    <th className="p-2 text-[10px] font-bold text-slate-500 uppercase">Odo</th>
                    <th className="p-2 text-[10px] font-bold text-slate-500 uppercase">Note</th>
                    <th className="p-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i} className="border-b border-slate-100">
                      <td className="p-2">
                        <select value={row.exp_type} onChange={(e) => setRow(i, "exp_type", e.target.value)} className="input h-8 w-auto py-0 text-xs">
                          {EXPENSE_TYPES.map((t) => (
                            <option key={t} value={t}>{t}</option>
                          ))}
                        </select>
                      </td>
                      <td className="p-2">
                        <input type="number" inputMode="decimal" min="0" step="any" value={row.amount} onChange={(e) => setRow(i, "amount", e.target.value)} className="input h-8 w-24 py-0 text-xs" placeholder="0" />
                      </td>
                      <td className="p-2">
                        <input type="number" inputMode="decimal" min="0" step="any" value={row.liters} onChange={(e) => setRow(i, "liters", e.target.value)} className="input h-8 w-20 py-0 text-xs" />
                      </td>
                      <td className="p-2">
                        <input type="number" inputMode="decimal" min="0" step="any" value={row.odometer} onChange={(e) => setRow(i, "odometer", e.target.value)} className="input h-8 w-24 py-0 text-xs" />
                      </td>
                      <td className="p-2">
                        <input type="text" value={row.note} onChange={(e) => setRow(i, "note", e.target.value)} className="input h-8 w-full min-w-[120px] py-0 text-xs" />
                      </td>
                      <td className="p-2">
                        <button type="button" onClick={() => setRows((rs) => rs.filter((_, idx) => idx !== i))} className="text-sm font-bold text-rose-500 hover:text-rose-700" aria-label="Remove row">✕</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {results && (
            <div className={`alert ${results.failed.length ? "alert-error" : "alert-success"}`}>
              Saved {results.saved}, queued {results.queued || 0}, failed {results.failed.length}.
              {results.failed.length > 0 && (
                <ul className="mt-1 list-disc pl-5 text-[11px]">
                  {results.failed.map((f, i) => <li key={i}>{f}</li>)}
                </ul>
              )}
            </div>
          )}

          <div className="flex gap-2">
            <button type="button" onClick={saveAll} disabled={busy || !rows.length} className="btn-primary flex-1 py-3 text-base disabled:opacity-50">
              {busy ? "Saving…" : `💾 Save All (${rows.length})`}
            </button>
            <button type="button" onClick={() => navigate(`/trips/${tripCode}/log`)} className="btn-secondary">
              Single entry
            </button>
          </div>
        </>
      )}
    </div>
  );
}


