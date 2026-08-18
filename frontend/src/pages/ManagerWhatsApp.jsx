import { useEffect, useState, useRef } from "react";
import { api } from "../lib/api.js";

function fmtRs(n) {
  return (Number(n) || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function ManagerWhatsAppPage() {
  const [escalations, setEscalations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const threadRef = useRef(null);

  async function refresh() {
    try {
      const list = await api.get("/api/v1/whatsapp/escalations");
      setEscalations(list || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, [escalations.length]);

  async function decide(exp, action) {
    setBusyId(exp.id);
    setError("");
    try {
      await api.post(`/api/v1/expenses/${exp.id}/action`, { action });
      await refresh();
    } catch (e) {
      setError(e.message || "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  const pending = escalations.filter(
    (e) => e.manager_status === "PENDING" || e.manager_status === null || e.manager_status === undefined
  );
  const resolved = escalations.filter(
    (e) => e.manager_status === "APPROVED" || e.manager_status === "REJECTED"
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-between items-center gap-2">
        <div>
          <h2 className="text-lg font-extrabold text-slate-900">Manager WhatsApp Escalation</h2>
          <p className="text-xs text-slate-500">
            Chat-style thread · flagged expenses routed to you for quick Approve / Deduct
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-amber-100 text-amber-700">
            {pending.length} pending
          </span>
          <span className="text-[10px] font-bold px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">
            {resolved.length} resolved
          </span>
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">{error}</div>
      )}

      {loading ? (
        <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center text-sm text-slate-400">
          Loading escalations…
        </div>
      ) : (
        <div className="max-w-3xl mx-auto bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden flex flex-col">
          <div className="bg-amber-800 text-white p-3.5 flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="w-9 h-9 rounded-full bg-amber-600 flex items-center justify-center font-bold text-sm">🔔</div>
              <div>
                <h3 className="text-sm font-bold leading-tight">Fleet Manager (WhatsApp)</h3>
                <p className="text-[10px] text-amber-200">Online • Anomaly Escalations</p>
              </div>
            </div>
          </div>

          <div ref={threadRef} className="flex-1 p-4 bg-[#efeae2] overflow-y-auto space-y-3 text-xs h-[480px]">
            <div className="bg-white p-3 rounded-lg rounded-tl-none shadow-sm max-w-[90%] space-y-1">
              <p className="font-bold text-slate-800 text-[11px]">🔔 Escalation Bot</p>
              <p className="text-slate-600">
                Flagged claims and goods transactions are routed here for your sign-off. Tap Approve or Deduct to respond.
              </p>
            </div>

            {escalations.length === 0 && (
              <div className="text-center text-slate-400 text-[11px] pt-6">
                All claims verified. Nothing pending.
              </div>
            )}
{escalations.map((e) => (
              <div key={e.id} className="space-y-1">
                <div className="flex flex-col items-start">
                  <div
                    className={`max-w-[90%] p-2.5 rounded-lg rounded-tl-none shadow-sm ${
                      e.is_flagged ? "bg-white border border-amber-200" : "bg-white border border-slate-200"
                    }`}
                  >
                    <p className="font-bold text-[11px] text-rose-700">
                      {e.is_flagged ? "⚠️" : "📦"} {e.exp_type} {e.is_flagged ? "Anomaly" : "Review"} — ₹{fmtRs(e.amount)}
                    </p>
                    <p className="text-[10px] text-slate-600">
                      {e.flag_reason || "Goods transactions require trip manager approval."}
                    </p>
                    <p className="text-[10px] text-slate-700 mt-0.5">
                      Trip: <strong>{e.trip_code}</strong>
                      {e.vehicle_no ? ` · Vehicle ${e.vehicle_no}` : ""}
                      {e.driver_name ? ` · ${e.driver_name}` : ""}
                      {e.liters ? ` · ${e.liters}L @ ₹${e.rate}/L` : ""}
                      {e.odometer ? ` · Odo ${e.odometer} KM` : ""}
                    </p>
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

                {e.manager_status === "PENDING" || e.manager_status === null || e.manager_status === undefined ? (
                  <div className="flex gap-1.5 max-w-[90%]">
                    <button
                      onClick={() => decide(e, "APPROVE")}
                      disabled={busyId === e.id}
                      className="text-[10px] bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-2.5 py-1 rounded-full transition disabled:opacity-50"
                    >
                      {busyId === e.id ? "…" : "✅ Approve"}
                    </button>
                    <button
                      onClick={() => decide(e, "REJECT")}
                      disabled={busyId === e.id}
                      className="text-[10px] bg-rose-600 hover:bg-rose-700 text-white font-bold px-2.5 py-1 rounded-full transition disabled:opacity-50"
                    >
                      {busyId === e.id ? "…" : "❌ Deduct"}
                    </button>
                  </div>
                ) : (
                  <div className="max-w-[90%]">
                    <span
                      className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                        e.manager_status === "APPROVED" ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
                      }`}
                    >
                      Resolved: {e.manager_status}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="p-3 bg-white border-t border-slate-200 text-center">
            <span className="text-[10px] text-slate-400">
              Approvals here update the Expense Ledger in real time.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}