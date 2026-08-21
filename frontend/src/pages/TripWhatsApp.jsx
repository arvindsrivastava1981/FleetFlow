import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";
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
  const [cashInHand, setCashInHand] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [trips, setTrips] = useState([]);

  const [form, setForm] = useState({
    trip_code: "", exp_type: "FUEL", amount: "", odometer: "", liters: "", rate: "", state_code: "",
  });
  const [states, setStates] = useState([]);
  const isFuelOrDef = form.exp_type === "FUEL" || form.exp_type === "DEF";
  const threadRef = useRef(null);

  useEffect(() => { api.get("/api/v1/states").then(setStates).catch(() => {}); }, []);

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
      setForm((f) => ({ ...f, trip_code: tripCode, state_code: tripData?.state_code || "" }));
      if (isDriver && tripData?.trip_code) {
        api.get("/api/v1/dashboard/overview").then((d) => setCashInHand(d?.cash_in_hand ?? 0));
      }
    }).catch((e) => { setError(e.message); toast.error(e.message); }).finally(() => setLoading(false));
  }, [tripCode, hasTripCode, isDriver]);
  useEffect(() => {
    if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, [expenses.length]);

  function onField(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  async function sendReceipt(e) {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    try {
      const payload = {
        trip_code: form.trip_code, exp_type: form.exp_type, amount: Number(form.amount),
        odometer: Number(form.odometer) || 0, liters: Number(form.liters) || 0,
        rate: Number(form.rate) || 0, state_code: form.state_code || undefined,
      };
      const res = await api.post("/api/v1/expenses", payload);
      const verdict = res?.verdict || (res?.is_flagged ? "flagged" : "ok");
      toast.success(verdict === "flagged"
        ? `⚠️ ${res?.flag_reason || "Expense flagged for manager review."}`
        : "✅ Receipt logged & verified.");
      setForm((f) => ({ ...f, amount: "", odometer: "", liters: "", rate: "" }));
      const det = await api.get(`/api/v1/trips/${tripCode}`);
      setExpenses(det?.expenses || []);
    } catch (e) { setError(e.message); toast.error(e.message); } finally { setBusy(false); }
  }

  async function decide(exp, action) {
    setBusyId(exp.id); setError("");
    try {
      const res = await api.post(`/api/v1/expenses/${exp.id}/action`, { action });
      const label = action === "APPROVE"
        ? (res?.label_hi ? `स्वीकृत (${res.label_en})` : "Expense approved ✅")
        : (res?.label_hi ? `कटौती (${res.label_en})` : "Expense deducted ❌");
      toast.success(label);
      const det = await api.get(`/api/v1/trips/${tripCode}`);
      setExpenses(det?.expenses || []);
    } catch (e) { setError(e.message || "Action failed"); toast.error(e.message || "Action failed"); }
    finally { setBusyId(null); }
  }

  const pending = expenses.filter((e) =>
    e.manager_status === "PENDING" || e.manager_status === null || e.manager_status === undefined);
  const resolved = expenses.filter((e) =>
    e.manager_status === "APPROVED" || e.manager_status === "REJECTED");

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
            <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-amber-100 text-amber-700">{pending.length} pending</span>
            <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">{resolved.length} resolved</span>
          </>)}
          {isDriver && <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">{expenses.length} logged</span>}
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {tripBar}

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
              {isDriver && <p className="text-slate-600">Owner Cash In: <strong className="text-emerald-700">₹{fmtRs(cashInHand)}</strong></p>}
              <p className="text-[10px] text-slate-400">{isDriver ? "Send a diesel or bill photo here." : "All trip transactions appear below."}</p>
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
                        {e.state_code && <p>📍 State: {e.state_code}</p>}
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col items-start">
                    <div className={`p-2.5 rounded-lg rounded-tl-none shadow-sm max-w-[85%] ${isFlaggedOrPending ? "bg-rose-50 border border-rose-200 text-rose-900" : "bg-white text-slate-800"}`}>
                      {isFlaggedOrPending ? (
                        <><p className="font-bold text-[11px]">⚠️ Pending Review (समीक्षा लंबित)</p>
                          <p className="text-[10px]">{e.flag_reason || "Needs trip manager approval."}</p></>
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
                      <div className="flex gap-1.5 max-w-[90%] mt-1">
                        <button onClick={() => decide(e, "APPROVE")} disabled={busyId === e.id}
                          className="text-[10px] btn-success px-2.5 py-1 rounded-full transition disabled:opacity-50">{busyId === e.id ? "…" : "✅ Approve"}</button>
                        <button onClick={() => decide(e, "REJECT")} disabled={busyId === e.id}
                          className="text-[10px] bg-rose-600 hover:bg-rose-700 text-white font-bold px-2.5 py-1 rounded-full transition disabled:opacity-50">{busyId === e.id ? "…" : "❌ Deduct"}</button>
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
            <form onSubmit={sendReceipt} className="p-3 bg-white border-t border-slate-200 space-y-2.5 flex-shrink-0">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-bold text-slate-500 block mb-1">Expense Type</label>
                  <select value={form.exp_type} onChange={(e) => onField("exp_type", e.target.value)} className="w-full text-xs input outline-none">
                    {EXPENSE_TYPES.map((t) => (<option key={t.value} value={t.value}>{t.label}</option>))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-500 block mb-1">Amount (₹)</label>
                  <input type="number" step="0.01" value={form.amount} onChange={(e) => onField("amount", e.target.value)}
                    placeholder="e.g. 4520" className="w-full text-xs input outline-none" />
                </div>
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
                      {states.map((s) => (<option key={s.code} value={s.code}>{s.code} · {s.name}</option>))}
                    </select>
                  </div>
                </>)}
                <div className={isFuelOrDef ? "" : "hidden"}>
                  <label className="text-[10px] font-bold text-slate-500 block mb-1">Odometer (KM)</label>
                  <input type="number" step="1" value={form.odometer} onChange={(e) => onField("odometer", e.target.value)}
                    placeholder="e.g. 103650" className="w-full text-xs input outline-none" />
                </div>
              </div>
              <button type="submit" disabled={busy} className="w-full btn-success text-xs py-2.5 rounded-xl transition disabled:opacity-50">
                {busy ? "Sending…" : "📤 Send receipt"}
              </button>
              <p className="text-[10px] text-slate-400 text-center">Simulates a WhatsApp message to the VahanKhata bot.</p>
            </form>
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