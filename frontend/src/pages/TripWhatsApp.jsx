import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";
import { enqueue, isNetworkError } from "../lib/offlineQueue.js";
import { useToast } from "../context/ToastContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import Loader from "../components/Loader.jsx";

const EXPENSE_TYPES = [
  { value: "FUEL", label: "Diesel (डीजल)" },
  { value: "DEF", label: "DEF (यूरिया)" },
  { value: "TOLL", label: "Toll (टोल)" },
  { value: "REPAIR", label: "Repair (मरम्मत)" },
  { value: "CHALLAN", label: "Challan (चालान)" },
  { value: "MISC", label: "Kanta / Misc (कांटा / विविध)" },
  { value: "GOODS_BUY", label: "Goods Buy (माल खरीद)" },
  { value: "GOODS_SALE", label: "Goods Sell (माल बिक्री)" },
];

const HINDI_LABELS = {
  FUEL: "डीजल", DEF: "यूरिया", TOLL: "टोल", REPAIR: "मरम्मत",
  CHALLAN: "चालान", MISC: "कांटा / विविध",
  GOODS_BUY: "माल खरीद", GOODS_SALE: "माल बिक्री",
  SETTLEMENT_TRANSFER: "हिसाब / सेटलमेंट",
};

const HINDI_STATUS = { APPROVED: "स्वीकृत", PENDING: "लंबित", REJECTED: "अस्वीकृत" };

function fmtRs(n) {
  return (Number(n) || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function TripWhatsAppPage() {
  const { tripCode } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const role = user?.role;
  const isDriver = role === "driver";
  const isManager = role === "trip_manager" || role === "super_admin";

  const [trip, setTrip] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [selected, setSelected] = useState(() => new Set()); // P-1 bulk approvals
  const [loading, setLoading] = useState(true);
  const [trips, setTrips] = useState([]);
  const [agree, setAgree] = useState(false); // settlement consent checkbox
  // Inline "why rejected?" note for the manager's Deduct action.
  const [rejectTarget, setRejectTarget] = useState(null);
  const [rejectNote, setRejectNote] = useState("");
  const [partialId, setPartialId] = useState(null);
  const [partialAmount, setPartialAmount] = useState("");

  const [form, setForm] = useState({
    trip_code: "", exp_type: "FUEL", amount: "", odometer: "", liters: "", rate: "", state_code: "", note: "",
  });
  const [states, setStates] = useState([]);
  const isFuelOrDef = form.exp_type === "FUEL" || form.exp_type === "DEF";
  // Options are DB-driven (?source=benchmarks -> fuel_benchmarks rows only);
  // ★ Favorites starred on the Rules & Rates page pin to the top of the picker.
  const sortedStates = [...states].sort(
    (a, b) =>
      Number(b.is_favorite === true) - Number(a.is_favorite === true) ||
      String(a.name).localeCompare(String(b.name)),
  );
  const favStates = sortedStates.filter((s) => s.is_favorite === true);
  const restStates = sortedStates.filter((s) => s.is_favorite !== true);
  const threadRef = useRef(null);

  useEffect(() => { api.get("/api/v1/states?source=benchmarks").then(setStates).catch(() => {}); }, []);

  // Fueling-state preselection: keep any already-chosen/trip state, else the
  // driver's top ★ favorite from Rules & Rates, else UP as the default.
  useEffect(() => {
    setForm((f) => {
      if (f.state_code) return f;
      const fav = states.find((s) => s.is_favorite === true);
      return { ...f, state_code: fav?.code || "UP" };
    });
  }, [states]);

  // Leaving the settlement type clears the consent checkbox.
  useEffect(() => {
    if (form.exp_type !== "SETTLEMENT_TRANSFER") setAgree(false);
  }, [form.exp_type]);

  useEffect(() => {
    if (isManager) {
      api.get("/api/v1/trips")
        .then((d) => setTrips((d?.trips || d || []).filter((t) => t.status === "ACTIVE")))
        .catch(() => {});
    }
  }, [isManager]);

  const hasTripCode = Boolean(tripCode);

  useEffect(() => {
    if (!hasTripCode && isDriver) {
      api.get("/api/v1/dashboard/overview").then((d) => {
        const t = d?.trip;
        if (t?.trip_code) { navigate(`/whatsapp/${t.trip_code}`, { replace: true }); }
        else { setLoading(false); }
      }).catch((e) => { setError(e.message); setLoading(false); });
      return;
    }
    if (!hasTripCode) { setLoading(false); return; }
    api.get(`/api/v1/trips/${tripCode}`).then((det) => {
      const tripData = det?.trip || det;
      setTrip(tripData);
      setExpenses(det?.expenses || []);
      setForm((f) => ({ ...f, trip_code: tripCode, state_code: tripData?.state_code || f.state_code || "" }));
    }).catch((e) => { setError(e.message); toast.error(e.message); }).finally(() => setLoading(false));
  }, [tripCode, hasTripCode, isDriver]);
  useEffect(() => {
    if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, [expenses.length]);

  function onField(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  async function sendReceipt(e) {
    e.preventDefault();
    if (busy) return;
    const isSettlementSend = form.exp_type === "SETTLEMENT_TRANSFER";
    const payload = {
      trip_code: form.trip_code, exp_type: form.exp_type,
      amount: isSettlementSend ? 0 : Number(form.amount),
      odometer: Number(form.odometer) || 0, liters: Number(form.liters) || 0,
      rate: Number(form.rate) || 0, state_code: form.state_code || undefined,
      ...((form.exp_type === "MISC" || isSettlementSend) && form.note.trim()
        ? { raw_receipt_text: form.note.trim() } : {}),
    };
    setBusy(true); setError("");
    try {
      const res = await api.post("/api/v1/expenses", payload);
      if (isSettlementSend) {
        toast.success(`🤝 Settlement request of ₹${fmtRs(res?.settlement_amount ?? settlementAmount)} sent to your manager for approval.`);
      } else {
        const verdict = res?.verdict || (res?.is_flagged ? "flagged" : "ok");
        toast.success(verdict === "flagged"
          ? `⚠️ ${res?.flag_reason || "Expense flagged for manager review."}`
          : "✅ Receipt logged & verified.");
      }
      setForm((f) => ({ ...f, amount: "", odometer: "", liters: "", rate: "", note: "" }));
      setAgree(false);
      const det = await api.get(`/api/v1/trips/${tripCode}`);
      setExpenses(det?.expenses || []);
    } catch (e) {
      if (!isSettlementSend && isNetworkError(e)) {
        enqueue(payload);
        toast.info("Saved offline — will sync when back online.");
        setForm((f) => ({ ...f, amount: "", odometer: "", liters: "", rate: "", note: "" }));
        setAgree(false);
      } else {
        setError(e.message); toast.error(e.message);
      }
    } finally { setBusy(false); }
  }

  async function decide(exp, action, approvedAmount) {
    setBusyId(exp.id); setError("");
    try {
      const res = await api.post(`/api/v1/expenses/${exp.id}/action`, {
        action,
        ...(action === "REJECT" && rejectNote.trim()
          ? { reason: rejectNote.trim() } : {}),
        ...(action === "APPROVE" && approvedAmount != null
          ? { approved_amount: Number(approvedAmount) } : {}),
      });
      const label = action === "APPROVE"
        ? (res?.label_hi ? `स्वीकृत (${res.label_en})` : "Expense approved ✅")
        : (res?.label_hi ? `${res.label_en} (${res.label_hi})` : "Expense deducted ❌");
      toast.success(label);
      setRejectTarget(null); setRejectNote("");
      setPartialId(null); setPartialAmount("");
      const det = await api.get(`/api/v1/trips/${tripCode}`);
      setExpenses(det?.expenses || []);
    } catch (e) { setError(e.message || "Action failed"); toast.error(e.message || "Action failed"); }
    finally { setBusyId(null); }
  }

  // ── P-1: bulk approvals ────────────────────────────────────────────────
  function toggleSel(id) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function bulkDecide(action) {
    if (!selected.size || busy) return;
    setBusy(true); setError("");
    let ok = 0, fail = 0;
    for (const id of selected) {
      try {
        await api.post(`/api/v1/expenses/${id}/action`, { action });
        ok += 1;
      } catch { fail += 1; }
    }
    toast.fail?.();
    toast.success(`${ok} expense${ok === 1 ? "" : "s"} ${action === "APPROVE" ? "approved" : "deducted"}${fail ? ` · ${fail} failed` : ""}`);
    setSelected(new Set());
    try {
      const det = await api.get(`/api/v1/trips/${tripCode}`);
      setExpenses(det?.expenses || []);
    } catch { /* refresh is best-effort */ }
    setBusy(false);
  }

  // Keyboard shortcuts (P-1): A = approve selected, D = deduct, Esc = clear.
  useEffect(() => {
    if (!isManager) return undefined;
    function onKey(e) {
      const tag = (e.target?.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if (e.key === "a" && selected.size) { e.preventDefault(); bulkDecide("APPROVE"); }
      if (e.key === "d" && selected.size) { e.preventDefault(); bulkDecide("REJECT"); }
      if (e.key === "Escape") setSelected(new Set());
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  /* ── Removed: standalone "Initiate Settlement" button — the driver now
     initiates the final settlement through the unified receipt form by
     choosing the SETTLEMENT_TRANSFER expense type (consent panel included). ── */

  const pending = expenses.filter((e) =>
    e.manager_status === "PENDING" || e.manager_status === null || e.manager_status === undefined);
  const resolved = expenses.filter((e) =>
    e.manager_status === "APPROVED" || e.manager_status === "REJECTED");

  // Live Dr/Cr balance (mirrors compute_settlement): advance + goods income −
  // (road expenses + driver batta). Only APPROVED ledger rows count.
  const approvedAmt = (e) => Number(e.approved_amount ?? e.amount) || 0;
  const balance = Math.round(100 * expenses
    .filter((e) => e.manager_status === "APPROVED" && e.exp_type !== "SETTLEMENT_TRANSFER")
    .reduce(
      (sum, e) => sum + (["CASH_ADVANCE", "GOODS_SALE"].includes(e.exp_type) ? approvedAmt(e) : -approvedAmt(e)),
      0,
    )) / 100;
  // The driver-initiated closing entry (acceptance). REJECTED frees the ledger.
  const transferRow = expenses.find((e) => e.exp_type === "SETTLEMENT_TRANSFER" && e.manager_status !== "REJECTED");

  // Unified settlement entry: the driver picks SETTLEMENT_TRANSFER in the
  // receipt form itself. The closing amount is server-computed from the live
  // approved ledger; GET /trips/{code} carries the authoritative figures
  // (net_balance + direction), with the client mirror as display fallback.
  const isSettlement = form.exp_type === "SETTLEMENT_TRANSFER";
  const isDriverRefund = Boolean(trip?.settlement?.is_driver_refund);
  const settlementAmount = Math.abs(
    Number(trip?.settlement?.net_balance ?? balance) || 0,
  );
  // The most recently REJECTED closing entry (if any) — shown so the driver
  // knows the request was declined and why; REJECTED frees the ledger again.
  const rejectedTransfer = expenses.find(
    (e) => e.exp_type === "SETTLEMENT_TRANSFER" && e.manager_status === "REJECTED",
  );

  /* ── Manager trip picker (no tripCode) ── */
  if (!hasTripCode && isManager && !loading) {
    return (
      <div className="space-y-4">
        <div><h2 className="page-title">WhatsApp View</h2>
          <p className="text-xs text-slate-500">Select an active trip to open its shared chat thread.</p></div>
        {trips.length === 0 ? (
          <div className="empty card">No active trips. Start one from Active Trips first.</div>
        ) : (
          <div className="grid gap-2 max-w-lg">
            {trips.map((t) => (
              <button key={t.trip_code} onClick={() => navigate(`/whatsapp/${t.trip_code}`)}
                className="card-pad text-left hover:border-brand-300 transition">
                <p className="font-bold text-sm">{t.trip_code}</p>
                <p className="text-[11px] text-slate-500">
                  {t.vehicle_no} · {t.driver_name || "—"} · ODO {t.current_odo ?? t.start_odo ?? "—"}
                </p>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  /* ── Driver no active trip ── */
  if (!hasTripCode && isDriver && !loading) {
    return (
      <div className="empty card">
        You have no active trip right now. A trip manager will assign one before your next dispatch.
      </div>
    );
  }

  if (loading) return <Loader label="Loading trip chat…" />;

  if (!trip) {
    return <div className="empty card">Trip <strong>{tripCode}</strong> not found or not accessible.</div>;
  }

  /* ── Trip selector bar (manager) ── */
  const tripBar = isManager && trips.length > 0 && (
    <div className="flex items-center gap-2 flex-wrap mb-3">
      <span className="text-[10px] font-bold text-slate-500 uppercase">Trip:</span>
      <select value={tripCode} onChange={(e) => navigate(`/whatsapp/${e.target.value}`)} className="text-xs input">
        {trips.map((t) => (
          <option key={t.trip_code} value={t.trip_code}>{t.trip_code} · {t.vehicle_no} · {t.driver_name || "—"}</option>
        ))}
      </select>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-between items-center gap-2">
        <div>
          <h2 className="page-title">WhatsApp View</h2>
          <p className="text-xs text-slate-500">
            {isDriver ? "Chat-style simulator · send expense receipts to VahanKhata bot"
              : "Chat-style thread · all trip transactions with bilingual detail"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isManager && (<>
            <button type="button" onClick={() => setSelected(new Set(pending.map((e) => e.id)))}
              className="text-[10px] font-bold px-2 py-1 rounded-full bg-ink-100 text-ink-600 hover:bg-ink-200 transition">
              Select pending ({pending.length})
            </button>
            <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-amber-100 text-amber-700">{pending.length} pending</span>
            <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">{resolved.length} resolved</span>
          </>)}
          {isDriver && <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">{expenses.length} logged</span>}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {tripBar}

      {isManager && selected.size > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5">
          <span className="text-xs font-bold text-amber-800">{selected.size} selected</span>
          <button type="button" onClick={() => bulkDecide("APPROVE")} disabled={busy}
            className="btn-success btn-sm rounded-full disabled:opacity-50">✅ Approve all (A)</button>
          <button type="button" onClick={() => bulkDecide("REJECT")} disabled={busy}
            className="rounded-full bg-rose-600 px-3 py-1 text-xs font-bold text-white transition hover:bg-rose-700 disabled:opacity-50">❌ Deduct all (D)</button>
          <button type="button" onClick={() => setSelected(new Set())} className="text-xs text-ink-500 underline">Clear (Esc)</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden flex flex-col h-[560px]">
          <div className={`${isDriver ? "bg-emerald-800" : "bg-amber-800"} text-white p-3.5 flex items-center justify-between flex-shrink-0`}>
            <div className="flex items-center space-x-2.5">
              <div className={`w-9 h-9 rounded-full ${isDriver ? "bg-emerald-600" : "bg-amber-600"} flex items-center justify-center font-bold text-sm`}>🤖</div>
              <div>
                <h3 className="text-sm font-bold leading-tight">VahanKhata Bot</h3>
                <p className={`text-[10px] ${isDriver ? "text-emerald-200" : "text-amber-200"}`}>Online · {isDriver ? "Automated Verification" : "Trip Chat"}</p>
              </div>
            </div>
            <span className={`text-[10px] ${isDriver ? "bg-emerald-900 text-emerald-200" : "bg-amber-900 text-amber-200"} px-2 py-0.5 rounded font-mono`}>{trip.vehicle_no}</span>
          </div>

          <div ref={threadRef} className="flex-1 min-h-0 p-4 bg-[#efeae2] overflow-y-auto space-y-3 text-xs wa-scroll">
            <div className="bg-white p-3 rounded-lg rounded-tl-none shadow-sm max-w-[85%] space-y-1">
              <p className="font-bold text-slate-800 text-[11px]">
                {isDriver ? `नमस्ते ${trip.driver_name || "Driver"} जी! 👋` : `Trip ${trip.trip_code} · ${trip.vehicle_no}`}
              </p>
              <p className="text-slate-600">
                {isDriver
                  ? <>Trip <strong>{trip.trip_code}</strong> started on vehicle <strong>{trip.vehicle_no}</strong>.</>
                  : <>Driver: <strong>{trip.driver_name || "—"}</strong> · Started by: <strong>{trip.created_by_name || "Manager"}</strong></>}
              </p>
              {isDriver && <p className="text-[10px] text-slate-400">Send a diesel or bill photo here.</p>}
              {!isDriver && <p className="text-[10px] text-slate-400">All trip transactions appear below.</p>}
            </div>

            {expenses.length === 0 && <div className="text-center text-slate-400 text-[11px] pt-6">No receipts logged yet.</div>}

            {[...expenses].reverse().map((e) => {
              const isFuel = e.exp_type === "FUEL";
              const needsAction = e.manager_status === "PENDING" || e.manager_status === null || e.manager_status === undefined;
              const isFlaggedOrPending = e.is_flagged || needsAction;

              return (
                <div key={e.id} className="space-y-1">
                  <div className="flex flex-col items-end">
                    <div className="bg-[#d9fdd3] p-2.5 rounded-lg rounded-tr-none shadow-sm max-w-[85%] text-slate-800">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-bold text-[11px]">📸 {e.exp_type} · {HINDI_LABELS[e.exp_type] || e.exp_type}</p>
                        <p className="font-extrabold text-[12px] text-emerald-700">₹{fmtRs(e.amount)}</p>
                      </div>
                      <div className="text-[10px] text-slate-600 space-y-0.5">
                        {(e.exp_type === "FUEL" || e.exp_type === "DEF") && <p>⛽ {e.liters} L (लीटर) × ₹{e.rate}/L</p>}
                        {Number(e.odometer) > 0 && <p>🛣️ Odometer: {e.odometer} KM (कि.मी.)</p>}
                        {e.station_name && <p>⛽ Station: {e.station_name}</p>}
                        {(e.exp_type === "FUEL" || e.exp_type === "DEF") && e.state_code && <p>📍 State: {e.state_code}</p>}
                        {e.exp_type === "MISC" && e.raw_receipt_text && <p>📝 {e.raw_receipt_text}</p>}
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col items-start">
                    <div className={`p-2.5 rounded-lg rounded-tl-none shadow-sm max-w-[85%] ${isFlaggedOrPending ? "bg-rose-50 border border-rose-200 text-rose-900" : "bg-white text-slate-800"}`}>
                      {isFlaggedOrPending ? (
                        <><p className="font-bold text-[11px]">⚠️ Pending Review (समीक्षा लंबित)</p>
                          <p className="text-[10px]">{e.flag_reason || "Needs trip manager approval."}</p></>
                      ) : e.manager_status === "REJECTED" ? (
                        <><p className="font-bold text-[11px]">❌ Rejected (अस्वीकृत)</p>
                          <p className="text-[10px]">{e.flag_reason || `${HINDI_LABELS[e.exp_type] || e.exp_type} · ₹${fmtRs(e.amount)} denied by manager.`}</p></>
                      ) : (
                        <><p className="font-bold text-[11px]">✅ Verified (सत्यापित)</p>
                          <p className="text-[10px]">{HINDI_LABELS[e.exp_type] || e.exp_type} · ₹{fmtRs(e.amount)} logged.</p></>
                      )}
                      {isFuel && <p className="text-[10px] text-slate-500">Status: {e.manager_status} ({HINDI_STATUS[e.manager_status] || "—"})</p>}
                      <p className="text-[9px] text-slate-400 mt-1">
                        {new Date(e.created_at).toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                    {isManager && needsAction && (
                      <div className="max-w-[90%] mt-1 space-y-1">
                        <div className="flex items-center gap-2">
                          <label className="flex items-center gap-1 text-[10px] text-slate-600">
                            <input type="checkbox" checked={selected.has(e.id)}
                              onChange={() => toggleSel(e.id)} className="accent-amber-600" />
                            select
                          </label>
                          <button onClick={() => decide(e, "APPROVE")} disabled={busyId === e.id}
                            className="text-[10px] btn-success px-3 py-1.5 min-h-[32px] rounded-full transition disabled:opacity-50">{busyId === e.id ? "…" : "✅ Approve"}</button>
                          <button
                            onClick={() => { setPartialAmount(String(e.amount || "")); setPartialId(partialId === e.id ? null : e.id); }}
                            disabled={busyId === e.id}
                            className="text-[10px] btn-secondary px-3 py-1.5 min-h-[32px] rounded-full transition disabled:opacity-50"
                            title="Approve a lower amount"
                          >
                            ✂️
                          </button>
                          <button
                            onClick={() => { setRejectNote(""); setRejectTarget(rejectTarget === e.id ? null : e.id); }}
                            disabled={busyId === e.id}
                            className="text-[10px] bg-rose-600 hover:bg-rose-700 text-white font-bold px-3 py-1.5 min-h-[32px] rounded-full transition disabled:opacity-50">
                            {rejectTarget === e.id ? "✕ Cancel" : busyId === e.id ? "…" : "❌ Deduct"}
                          </button>
                        </div>
                        {rejectTarget === e.id && (
                          <div className="flex items-center gap-1.5 bg-rose-50 border border-rose-200 rounded-full px-2.5 py-1">
                            <input value={rejectNote} onChange={(ev) => setRejectNote(ev.target.value)}
                              placeholder="Reason (optional)… e.g. receipt missing" maxLength={500}
                              className="flex-1 min-w-0 bg-transparent text-[10px] text-rose-900 outline-none placeholder:text-rose-300" />
                            <button onClick={() => decide(e, "REJECT")} disabled={busyId === e.id}
                              className="text-[10px] font-bold bg-rose-600 text-white px-3 py-1 min-h-[32px] rounded-full transition disabled:opacity-50">
                              {busyId === e.id ? "…" : "Confirm"}
                            </button>
                          </div>
                        )}
                        {partialId === e.id && (
                          <div className="flex items-center gap-1.5 bg-emerald-50 border border-emerald-200 rounded-full px-2.5 py-1">
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              value={partialAmount}
                              onChange={(e) => setPartialAmount(e.target.value)}
                              placeholder="Approved ₹"
                              className="flex-1 min-w-0 bg-transparent text-[10px] text-emerald-900 outline-none placeholder:text-emerald-300"
                            />
                            <button
                              onClick={() => decide(e, "APPROVE", partialAmount)}
                              disabled={busyId === e.id || !partialAmount || Number(partialAmount) <= 0 || Number(partialAmount) > Number(e.amount)}
                              className="text-[10px] font-bold bg-emerald-600 text-white px-3 py-1 min-h-[32px] rounded-full transition disabled:opacity-50"
                            >
                              {busyId === e.id ? "…" : "Approve ₹"}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                    {isManager && !needsAction && (
                      <div className="max-w-[90%] mt-1">
                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${e.manager_status === "APPROVED" ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>Resolved: {e.manager_status}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {isDriver && (
            transferRow ? (
              <div className="p-3 bg-slate-50 border-t border-slate-200">
                <p className="text-[10px] font-bold text-slate-700">🔒 Ledger locked / हिसाब लॉक है</p>
                <p className="text-[10px] text-slate-500">
                  Settlement request {transferRow.manager_status === "PENDING" ? "awaiting manager approval" : "approved"} —
                  new receipts are blocked until the trip is settled.
                </p>
              </div>
            ) : (
            <form onSubmit={sendReceipt} className="p-3 bg-white border-t border-slate-200 space-y-2.5 flex-shrink-0">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-bold text-slate-500 block mb-1">Expense Type</label>
                  <select value={form.exp_type} onChange={(e) => onField("exp_type", e.target.value)} className="w-full text-xs input outline-none">
                    {EXPENSE_TYPES.map((t) => (<option key={t.value} value={t.value}>{t.label}</option>))}
                    {isDriver && (
                      <option value="SETTLEMENT_TRANSFER">🤝 Settlement / हिसाब</option>
                    )}
                  </select>
                </div>
                {isSettlement ? (
                  <div className="col-span-2 bg-amber-50 border border-amber-300 p-2.5 rounded-xl">
                    <p className="text-[10px] font-bold text-amber-900">
                      ⚠️ यह आपका अंतिम हिसाब अनुरोध है — आप ₹{fmtRs(settlementAmount)}{" "}
                      {isDriverRefund ? "मालिक को वापस करने के लिए" : "प्राप्त करने के लिए"} सहमत हैं।
                    </p>
                    <p className="text-[10px] text-amber-800 mt-0.5">
                      This is your final settlement request — you agree to{" "}
                      {isDriverRefund
                        ? `return ₹${fmtRs(settlementAmount)} to the Owner`
                        : `receive ₹${fmtRs(settlementAmount)} from the Owner`}
                      . The amount is auto-calculated from the approved ledger;
                      manager approval records your acceptance.
                    </p>
                    <label className="flex items-center gap-2 mt-2 text-[10px] font-extrabold text-amber-900">
                      <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
                      I agree / मैं सहमत हूँ
                    </label>
                  </div>
                ) : (
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 block mb-1">Amount (₹)</label>
                    <input type="number" step="0.01" value={form.amount} onChange={(e) => onField("amount", e.target.value)}
                      placeholder="e.g. 4520" className="w-full text-xs input outline-none" />
                  </div>
                )}
                {(form.exp_type === "MISC" || isSettlement) && (
                  <div className="col-span-2">
                    <label className="text-[10px] font-bold text-slate-500 block mb-1">Description (optional) / विवरण (वैकल्पिक)</label>
                    <input type="text" value={form.note} onChange={(e) => onField("note", e.target.value)}
                      placeholder="Kis liye? e.g. Kanta at Bareilly weighbridge" maxLength={500}
                      className="w-full text-xs input outline-none" />
                  </div>
                )}
                {isFuelOrDef && (<>
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 block mb-1">Liters</label>
                    <input type="number" step="0.01" value={form.liters} onChange={(e) => onField("liters", e.target.value)}
                      placeholder="e.g. 50" className="w-full text-xs input outline-none" />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 block mb-1">Rate (₹/L)</label>
                    <input type="number" step="0.01" value={form.rate} onChange={(e) => onField("rate", e.target.value)}
                      placeholder="e.g. 90.50" className="w-full text-xs input outline-none" />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-500 block mb-1">Fueling State</label>
                    <select value={form.state_code} onChange={(e) => onField("state_code", e.target.value)} className="w-full text-xs input outline-none">
                      <option value="">Select state</option>
                      {favStates.length > 0 && (
                        <optgroup label="★ Favorites by manager">
                          {favStates.map((s) => (<option key={s.code} value={s.code}>★ {s.code} · {s.name}</option>))}
                        </optgroup>
                      )}
                      <optgroup label="All states">
                        {restStates.map((s) => (<option key={s.code} value={s.code}>{s.code} · {s.name}</option>))}
                      </optgroup>
                    </select>
                  </div>
                </>)}
                <div className={isFuelOrDef ? "" : "hidden"}>
                  <label className="text-[10px] font-bold text-slate-500 block mb-1">Odometer (KM)</label>
                  <input type="number" step="1" value={form.odometer} onChange={(e) => onField("odometer", e.target.value)}
                    placeholder="e.g. 103650" className="w-full text-xs input outline-none" />
                </div>
              </div>
              <button type="submit" disabled={busy || (isSettlement && !agree)}
                className="w-full btn-success text-xs py-2.5 rounded-xl transition disabled:opacity-50">
                {busy ? "Sending…" : isSettlement ? "🤝 Send settlement request" : "📤 Send receipt"}
              </button>
              <p className="text-[10px] text-slate-400 text-center">Simulates a WhatsApp message to the VahanKhata bot.</p>
            </form>
            )
          )}

        </div>

        <div className="card-pad space-y-3 h-fit">
          <h3 className="text-sm font-extrabold text-slate-800">Active Trip</h3>
          <div className="grid grid-cols-2 gap-2.5 text-center">
            <div className="bg-slate-50 border border-slate-200 p-2.5 rounded-xl">
              <span className="text-[9px] uppercase font-bold text-slate-500 block">Trip Code</span>
              <span className="text-xs font-bold text-slate-800">{trip.trip_code}</span>
            </div>
            <div className="bg-slate-50 border border-slate-200 p-2.5 rounded-xl">
              <span className="text-[9px] uppercase font-bold text-slate-500 block">Vehicle</span>
              <span className="text-xs font-bold text-slate-800">{trip.vehicle_no}</span>
            </div>
            <div className="bg-emerald-50 border border-emerald-200 p-2.5 rounded-xl text-emerald-800">
              <span className="text-[9px] uppercase font-bold block">Receipts Logged</span>
              <span className="text-xs font-bold">{expenses.length}</span>
            </div>
            {isManager && (
              <div className="bg-slate-50 border border-slate-200 p-2.5 rounded-xl">
                <span className="text-[9px] uppercase font-bold text-slate-500 block">Driver</span>
                <span className="text-xs font-bold text-slate-800">{trip.driver_name || "—"}</span>
              </div>
            )}
          </div>
          {isDriver && (
            <div className="pt-2 border-t border-slate-100">
              {transferRow ? (
                transferRow.manager_status === "APPROVED" ? (
                  <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-2.5 rounded-xl">
                    <p className="text-[10px] font-bold">✅ Driver acceptance recorded / स्वीकृति दर्ज</p>
                    <p className="text-[10px]">Settlement cash ₹{fmtRs(transferRow.approved_amount ?? transferRow.amount)} — manager can now settle the trip.</p>
                  </div>
                ) : (
                  <div className="bg-amber-50 border border-amber-200 text-amber-800 p-2.5 rounded-xl">
                    <p className="text-[10px] font-bold">🤝 Awaiting manager approval / स्वीकृति लंबित</p>
                    <p className="text-[10px]">You accepted the settlement balance of ₹{fmtRs(transferRow.amount)}. Expenses are locked until reviewed.</p>
                  </div>
                )
              ) : (
                <>
                  {rejectedTransfer && (
                    <div className="bg-rose-50 border border-rose-200 text-rose-800 p-2.5 rounded-xl mb-2">
                      <p className="text-[10px] font-bold">❌ Settlement request rejected / हिसाब अस्वीकृत</p>
                      {rejectedTransfer.flag_reason && (
                        <p className="text-[10px]">Manager note / कारण: {rejectedTransfer.flag_reason}</p>
                      )}
                      <p className="text-[10px]">Log any corrections, then send a fresh 🤝 Settlement / हिसाब request from the receipt form.</p>
                    </div>
                  )}
                  <div className="bg-slate-50 border border-slate-200 p-2.5 rounded-xl">
                    <span className="text-[9px] uppercase font-bold text-slate-500 block">Current Balance / वर्तमान शेष</span>
                    <span className={`text-sm font-extrabold ${balance < 0 ? "text-rose-600" : balance > 0 ? "text-slate-800" : "text-emerald-600"}`}>
                      ₹{fmtRs(Math.abs(balance))} {balance > 0 ? "refundable" : balance < 0 ? "payable" : "settled"}
                    </span>
                  </div>
                  <p className="text-[9px] text-slate-400 mt-1">
                    Final settlement? Choose “🤝 Settlement / हिसाब” as the expense type in the receipt form — the amount is auto-calculated.
                  </p>
                </>
              )}
            </div>
          )}
          {isManager && (
            <div className="pt-2 border-t border-slate-100">
              <p className="text-[10px] text-slate-400">Pending items need your approval. Approved items feed into settlement.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}