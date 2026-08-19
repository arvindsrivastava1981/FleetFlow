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
    <div className="space-y-5">
      <div>
        <h2 className="page-title">Billing &amp; Subscription</h2>
        <p className="page-sub">Manage your plan and add extra vehicle slots.</p>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {!data && !error && (
        <div className="empty card">
          <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-ink-200 border-t-brand-600" />
          <p className="mt-3">Loading billing info…</p>
        </div>
      )}
      {fleet && (
        <div className="card-pad grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <p className="stat-label">Fleet</p>
            <p className="mt-1 text-sm font-bold text-ink-800">{fleet.name}</p>
          </div>
          <div>
            <p className="stat-label">Subscription</p>
            <p className="mt-1 text-sm font-bold text-ink-800">
              {(fleet.subscription_status || "TRIAL").replace(/_/g, " ").toUpperCase()}
            </p>
          </div>
          <div>
            <p className="stat-label">Vehicle Slots</p>
            <p className="mt-1 text-sm font-bold text-ink-800">
              {fleet.vehicle_count} / {fleet.vehicle_limit}
            </p>
          </div>
        </div>
      )}
      {data?.plans && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {data.plans.map((p) => (
            <div key={p.code} className="card flex flex-col gap-3 p-5">
              <div>
                <p className="font-extrabold text-ink-900">{p.name}</p>
                <p className="text-sm text-ink-500">{p.description}</p>
                <p className="mt-2 text-3xl font-black text-ink-900">
                  ₹{p.price.toLocaleString("en-IN")}
                  <span className="text-sm font-semibold text-ink-500"> / {p.period}</span>
                </p>
              </div>
              <button
                onClick={() => subscribe(p.code)}
                disabled={busy === p.code}
                className={`${p.code === "TRIAL" ? "btn-secondary" : "btn-primary"} mt-auto w-full`}
              >
                {p.code === "TRIAL" ? "Start Trial" : "Pay Now"}
              </button>
            </div>
          ))}
        </div>
      )}

      {fleet && (
        <div className="card-pad flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-bold text-ink-800">Extra Vehicle Slot</p>
            <p className="text-sm text-ink-500">
              Add one more vehicle capacity — ₹{fleet.vehicle_slot_price?.toLocaleString("en-IN")}
            </p>
          </div>
          <button onClick={buySlot} disabled={busy === "slot"} className="btn-secondary">
            Buy Slot
          </button>
        </div>
      )}
    </div>
  );
}