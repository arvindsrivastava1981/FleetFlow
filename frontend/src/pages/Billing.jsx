import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

export default function BillingPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    api
      .get("/api/v1/billing/overview")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  async function subscribe(planCode) {
    setBusy(planCode);
    setError("");
    try {
      const res = await api.post("/api/v1/billing/subscribe", { plan_code: planCode });
      if (res?.redirect_url) {
        window.location.href = res.redirect_url;
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  async function buySlot() {
    setBusy("slot");
    setError("");
    try {
      const res = await api.post("/api/v1/billing/vehicle-slot", {});
      if (res?.redirect_url) {
        window.location.href = res.redirect_url;
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  const fleet = data?.fleet;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-extrabold text-slate-900">Billing &amp; Subscription</h2>
        <p className="text-xs text-slate-500">
          Manage your plan and add extra vehicle slots.
        </p>
      </div>
      {error && (
        <p className="text-xs text-rose-600 font-semibold bg-rose-50 border border-rose-200 rounded-lg p-3">
          {error}
        </p>
      )}
      {!data && !error && (
        <p className="text-xs text-slate-400">Loading billing info…</p>
      )}
      {fleet && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-[10px] font-bold uppercase text-slate-500">Fleet</p>
            <p className="text-sm font-bold text-slate-800">{fleet.name}</p>
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase text-slate-500">Subscription</p>
            <p className="text-sm font-bold text-slate-800">
              {(fleet.subscription_status || "TRIAL").replace(/_/g, " ").toUpperCase()}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase text-slate-500">Vehicle Slots</p>
            <p className="text-sm font-bold text-slate-800">
              {fleet.vehicle_count} / {fleet.vehicle_limit}
            </p>
          </div>
        </div>
      )}
      {data?.plans && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.plans.map((p) => (
            <div
              key={p.code}
              className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col gap-3"
            >
              <div>
                <p className="text-sm font-extrabold text-slate-900">{p.name}</p>
                <p className="text-xs text-slate-500">{p.description}</p>
                <p className="text-2xl font-black text-slate-900 mt-2">
                  ₹{p.price.toLocaleString("en-IN")}
                  <span className="text-xs text-slate-500 font-semibold"> / {p.period}</span>
                </p>
              </div>
              <button
                onClick={() => subscribe(p.code)}
                disabled={busy === p.code}
                className="bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold py-2.5 rounded-xl transition disabled:opacity-50"
              >
                {p.code === "TRIAL" ? "Start Trial" : "Pay Now"}
              </button>
            </div>
          ))}
        </div>
      )}

      {fleet && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-bold text-slate-800">Extra Vehicle Slot</p>
            <p className="text-xs text-slate-500">
              Add one more vehicle capacity — ₹{fleet.vehicle_slot_price?.toLocaleString("en-IN")}
            </p>
          </div>
          <button
            onClick={buySlot}
            disabled={busy === "slot"}
            className="bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition disabled:opacity-50"
          >
            Buy Slot
          </button>
        </div>
      )}
    </div>
  );
}