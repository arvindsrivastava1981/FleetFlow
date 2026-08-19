import { useEffect, useState, useRef } from "react";
import { api } from "../lib/api.js";

const EXPENSE_TYPES = // Quick Copy Array:
[
  { value: "FUEL", label: "Diesel (डीजल)" },
  { value: "DEF", label: "DEF (यूरिया)" },
  { value: "TOLL", label: "Toll (टोल)" },
  { value: "REPAIR", label: "Repair (मरम्मत)" },
  { value: "CHALLAN", label: "Challan (चालान)" },
  { value: "MISC", label: "Kanta / Misc (कांटा / विविध)" },
  { value: "GOODS_BUY", label: "Goods Buy (माल खरीद)" },
  { value: "GOODS_SALE", label: "Goods Sell (माल बिक्री)" }
];

function fmtRs(n) {
  return (Number(n) || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function DriverWhatsAppPage() {
  const [trip, setTrip] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");

  const [form, setForm] = useState({
    trip_code: "",
    exp_type: "FUEL",
    amount: "",
    odometer: "",
    liters: "",
    rate: "",
  });
  const isFuelOrDef = form.exp_type === "FUEL" || form.exp_type === "DEF";
  const threadRef = useRef(null);

  useEffect(() => {
    api
      .get("/api/v1/dashboard/overview")
      .then((d) => {
        const t = d?.trip;
        setTrip(t || null);
        if (t?.trip_code) {
          setForm((f) => ({ ...f, trip_code: t.trip_code }));
          return api.get(`/api/v1/trips/${t.trip_code}`);
        }
        return null;
      })
      .then((det) => {
        if (det) setExpenses(det.expenses || []);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, [expenses.length]);

  function onField(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }
async function sendReceipt(e) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setToast("");
    try {
      const payload = {
        trip_code: form.trip_code,
        exp_type: form.exp_type,
        amount: Number(form.amount),
        odometer: Number(form.odometer || 0),
        liters: Number(form.liters || 0),
        rate: Number(form.rate || 0),
      };
      const res = await api.post("/api/v1/expenses", payload);
      setToast(
        `Receipt logged: ${res.exp_type} ₹${fmtRs(payload.amount)} — ${
          res.is_flagged ? "⚠️ flagged for manager review" : "✅ verified"
        }`
      );
      const det = await api.get(`/api/v1/trips/${form.trip_code}`);
      setExpenses(det?.expenses || []);
      setForm((f) => ({ ...f, amount: "", odometer: "", liters: "", rate: "" }));
      setTimeout(() => setToast(""), 4000);
    } catch (err) {
      setToast(err.message || "Failed to send receipt");
      setTimeout(() => setToast(""), 4000);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-between items-center gap-2">
        <div>
          <h2 className="page-title">Driver (WhatsApp)</h2>
          <p className="text-xs text-slate-500">
            Chat-style simulator · driver sends expense receipts to the VahanKhata bot
          </p>
        </div>
        <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">
          {trip ? `Trip: ${trip.trip_code}` : "No active trip"}
        </span>
      </div>

      {error && (
        <div className="alert alert-error">{error}</div>
      )}
      {toast && (
        <div className="bg-brand-50 border border-sky-200 text-sky-800 text-sm rounded-xl p-3">{toast}</div>
      )}
{!trip ? (
        <div className="empty card">
          You have no active trip right now. A trip manager will assign one before your next dispatch.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden flex flex-col h-[560px]">
            <div className="bg-emerald-800 text-white p-3.5 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center space-x-2.5">
                <div className="w-9 h-9 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-sm">🤖</div>
                <div>
                  <h3 className="text-sm font-bold leading-tight">VahanKhata Bot</h3>
                  <p className="text-[10px] text-emerald-200">Online • Automated Verification</p>
                </div>
              </div>
              <span className="text-[10px] bg-emerald-900 text-emerald-200 px-2 py-0.5 rounded font-mono">
                {trip.vehicle_no}
              </span>
            </div>

            <div
              ref={threadRef}
              className="flex-1 min-h-0 p-4 bg-[#efeae2] overflow-y-auto space-y-3 text-xs wa-scroll"
            >
              <div className="bg-white p-3 rounded-lg rounded-tl-none shadow-sm max-w-[85%] space-y-1">
                <p className="font-bold text-slate-800 text-[11px]">
                  नमस्ते {trip.driver_name || "Driver"} जी! 👋
                </p>
                <p className="text-slate-600">
                  Trip <strong>{trip.trip_code}</strong> started on vehicle{" "}
                  <strong>{trip.vehicle_no}</strong>.
                </p>
                <p className="text-slate-600">
                  Owner Cash In: <strong className="text-emerald-700">₹{fmtRs(trip.advance_amount)}</strong>
                </p>
                <p className="text-[10px] text-slate-400">Send a diesel or bill photo here.</p>
              </div>

              {expenses.length === 0 && (
                <div className="text-center text-slate-400 text-[11px] pt-6">
                  No receipts logged yet. Use the form below to send one.
                </div>
              )}
{[...expenses].reverse().map((e) => (
                <div key={e.id} className="space-y-1">
                  <div className="flex flex-col items-end">
                    <div className="bg-[#d9fdd3] p-2.5 rounded-lg rounded-tr-none shadow-sm max-w-[85%] text-slate-800">
                      <p className="font-bold text-[11px]">
                        📸 {e.exp_type}: ₹{fmtRs(e.amount)}
                      </p>
                      <p className="text-[10px] text-slate-600">
                        {e.exp_type === "FUEL" || e.exp_type === "DEF"
                          ? `${e.liters}L @ ₹${e.rate}/L | Odo: ${e.odometer} KM`
                          : `Odo: ${e.odometer} KM`}
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-col items-start">
                    <div
                      className={`p-2.5 rounded-lg rounded-tl-none shadow-sm max-w-[85%] ${
                        e.is_flagged
                          ? "bg-rose-50 border border-rose-200 text-rose-900"
                          : "bg-white text-slate-800"
                      }`}
                    >
                      {e.is_flagged ? (
                        <>
                          <p className="font-bold text-[11px]">⚠️ Anomaly Alert</p>
                          <p className="text-[10px]">{e.flag_reason}</p>
                        </>
                      ) : (
                        <>
                          <p className="font-bold text-[11px]">✅ Verified</p>
                          <p className="text-[10px]">
                            ₹{fmtRs(e.amount)} logged and verified.
                          </p>
                        </>
                      )}
                      <p className="text-[9px] text-slate-400 mt-1">
                        {new Date(e.created_at).toLocaleString("en-IN", {
                          day: "2-digit",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
<form
              onSubmit={sendReceipt}
              className="p-3 bg-white border-t border-slate-200 space-y-2.5 flex-shrink-0"
            >
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-bold text-slate-500 block mb-1">Expense Type</label>
                  <select
                    value={form.exp_type}
                    onChange={(e) => onField("exp_type", e.target.value)}
                    className="w-full text-xs input outline-none"
                  >
                    {EXPENSE_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-500 block mb-1">Amount (₹)</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    value={form.amount}
                    onChange={(e) => onField("amount", e.target.value)}
                    placeholder="e.g. 2500"
                    className="w-full text-xs input outline-none"
                  />
                </div>
                {isFuelOrDef && (
                  <>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 block mb-1">Liters (L)</label>
                      <input
                        type="number" step="0.01" value={form.liters}
                        onChange={(e) => onField("liters", e.target.value)}
                        placeholder="e.g. 30"
                        className="w-full text-xs input outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-500 block mb-1">Rate (₹/L)</label>
                      <input
                        type="number" step="0.01" value={form.rate}
                        onChange={(e) => onField("rate", e.target.value)}
                        placeholder="e.g. 90.50"
                        className="w-full text-xs input outline-none"
                      />
                    </div>
                  </>
                )}
                <div className={isFuelOrDef ? "" : "hidden"}>
                  <label className="text-[10px] font-bold text-slate-500 block mb-1">Odometer (KM)</label>
                  <input
                    type="number" step="1" value={form.odometer}
                    onChange={(e) => onField("odometer", e.target.value)}
                    placeholder="e.g. 103650"
                    className="w-full text-xs input outline-none"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={busy}
                className="w-full btn-success text-xs py-2.5 rounded-xl transition disabled:opacity-50"
              >
                {busy ? "Sending…" : "📤 Send receipt"}
              </button>
              <p className="text-[10px] text-slate-400 text-center">
                Simulates a WhatsApp message to the VahanKhata bot.
              </p>
            </form>
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
              <div className="bg-brand-50 border border-sky-200 p-2.5 rounded-xl text-sky-800">
                <span className="text-[9px] uppercase font-bold block">Owner Cash In</span>
                <span className="text-xs font-bold">₹{fmtRs(trip.advance_amount)}</span>
              </div>
              <div className="bg-violet-50 border border-violet-200 p-2.5 rounded-xl text-violet-800">
                <span className="text-[9px] uppercase font-bold block">Driver Salary</span>
                <span className="text-xs font-bold">₹{fmtRs(trip.driver_batta_amount)}</span>
              </div>
              <div className="bg-emerald-50 border border-emerald-200 p-2.5 rounded-xl text-emerald-800">
                <span className="text-[9px] uppercase font-bold block">Receipts Logged</span>
                <span className="text-xs font-bold">{expenses.length}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}