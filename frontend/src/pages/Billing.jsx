import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import Loader from "../components/Loader.jsx";

const STATUS_BADGES = {
  TRIAL: "bg-amber-100 text-amber-800",
  ACTIVE: "bg-emerald-100 text-emerald-800",
  PAST_DUE: "bg-red-100 text-red-800",
  CANCELLED: "bg-gray-100 text-gray-600",
  EXPIRED: "bg-gray-100 text-gray-600",
};

function statusLabel(s) {
  return (s || "?").replace(/_/g, " ").toUpperCase();
}

function fmtDate(d) {
  if (!d) return "—";
  const s = typeof d === "string" ? d : d;
  return s.slice(0, 10);
}

/* ── Manager view ─────────────────────────────────────────────────────── */
function ManagerSubscription({ fleet, plans, onAction }) {
  const currentPlanCode = fleet?.plan_code;
  const currentStatus = fleet?.subscription_status;

  return (
    <div className="space-y-5">
      {/* Current plan card */}
      <div className="card-pad space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-ink-400">
              Current Plan
            </p>
            <p className="text-xl font-extrabold text-ink-900">
              {fleet?.plan_code || "NONE"}
              <span
                className={`ml-2 inline-block rounded-full px-2 py-0.5 text-[11px] font-bold ${STATUS_BADGES[currentStatus] || "bg-ink-100 text-ink-600"}`}
              >
                {statusLabel(currentStatus)}
              </span>
            </p>
          </div>
          <div className="flex items-center gap-3 text-sm text-ink-600">
            <div>
              <span className="text-ink-400">Vehicles:</span>{" "}
              <strong>{fleet?.vehicle_count}/{fleet?.vehicle_limit}</strong>
            </div>
            {fleet?.next_billing_date && (
              <div>
                <span className="text-ink-400">Next billing:</span>{" "}
                <strong>{fmtDate(fleet.next_billing_date)}</strong>
              </div>
            )}
            {fleet?.trial_ends_at && (
              <div>
                <span className="text-ink-400">Trial ends:</span>{" "}
                <strong>{fmtDate(fleet.trial_ends_at)}</strong>
              </div>
            )}
          </div>
        </div>
        {currentStatus !== "TRIAL" && (
          <button
            onClick={() => onAction("renew", currentPlanCode)}
            className="btn-primary"
          >
            Renew {currentPlanCode}
          </button>
        )}
      </div>

      {/* Plans grid */}
      <div>
        <h3 className="text-lg font-bold text-ink-800">
          {currentStatus === "TRIAL" ? "Upgrade Your Plan" : "Available Plans"}
        </h3>
        <p className="text-sm text-ink-500">
          Plans and pricing from our subscription catalogue.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {plans.map((p) => {
          const isCurrent = p.code === currentPlanCode;
          let periodLabel = p.period;
          if (p.trial_days > 0) periodLabel = `${p.trial_days} days`;
          else if (p.period === "MONTHLY") periodLabel = "month";
          else if (p.period === "YEARLY") periodLabel = "year";

          return (
            <div
              key={p.code}
              className={`card flex flex-col gap-3 p-5 ${isCurrent ? "ring-2 ring-brand-500" : ""}`}
            >
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-extrabold text-ink-900">{p.name}</p>
                  {isCurrent && (
                    <span className="rounded-full bg-brand-100 px-2 py-0.5 text-[10px] font-bold text-brand-700">
                      CURRENT
                    </span>
                  )}
                </div>
                <p className="text-sm text-ink-500">{p.description}</p>
                <p className="mt-2 text-3xl font-black text-ink-900">
                  ₹{p.price.toLocaleString("en-IN")}
                  <span className="text-sm font-semibold text-ink-500">
                    {" "}
                    / {periodLabel}
                  </span>
                </p>
              </div>
              {!isCurrent && (
                <button
                  onClick={() => onAction("subscribe", p.code)}
                  className={`${p.code === "TRIAL" ? "btn-secondary" : "btn-primary"} mt-auto w-full`}
                >
                  {p.code === "TRIAL" ? "Start Trial" : "Choose Plan"}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Extra slot card */}
      <div className="card-pad flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-bold text-ink-800">Extra Vehicle Slot</p>
          <p className="text-sm text-ink-500">
            Add one more vehicle — ₹
            {fleet?.vehicle_slot_price?.toLocaleString("en-IN") || "799"}
          </p>
        </div>
        <button onClick={() => onAction("slot")} className="btn-secondary">
          Buy Slot
        </button>
      </div>
        </div>
  );
}

/* ── Super Admin table ─────────────────────────────────────────────────── */
function AdminSubscriptionTable({ subscriptions, onRenew }) {
  if (!subscriptions || subscriptions.length === 0) {
    return (
      <div className="card-pad text-center text-ink-400">No fleets found.</div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-ink-200 text-xs font-bold uppercase text-ink-400">
            <th className="px-3 py-3">Fleet</th>
            <th className="px-3 py-3">Plan</th>
            <th className="px-3 py-3">Status</th>
            <th className="px-3 py-3">Vehicles</th>
            <th className="px-3 py-3">Next Billing</th>
            <th className="px-3 py-3">Trial Ends</th>
            <th className="px-3 py-3">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-100">
          {subscriptions.map((s) => (
            <tr key={s.fleet_id} className="hover:bg-ink-50">
              <td className="px-3 py-3 font-medium text-ink-900">
                {s.owner_name}
                <div className="text-xs text-ink-400">{s.phone}</div>
              </td>
              <td className="px-3 py-3 font-semibold">{s.plan_name || "—"}</td>
                            <td className="px-3 py-3">
                <span
                  className={`inline-block rounded-full px-2 py-0.5 text-[11px] font-bold ${STATUS_BADGES[s.subscription_status] || "bg-ink-100 text-ink-600"}`}
                >
                  {statusLabel(s.subscription_status)}
                </span>
              </td>
              <td className="px-3 py-3">{s.vehicle_count}/{s.vehicle_limit}</td>
              <td className="px-3 py-3">{fmtDate(s.next_billing_date)}</td>
              <td className="px-3 py-3">{fmtDate(s.trial_ends_at)}</td>
              <td className="px-3 py-3">
                {s.subscription_status !== "TRIAL" &&
                  s.subscription_status !== "CANCELLED" &&
                  s.subscription_status !== "EXPIRED" && (
                    <button
                      onClick={() => onRenew(s.fleet_id, s.plan_code)}
                      className="btn-secondary text-xs"
                    >
                      Renew
                    </button>
                  )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────────────────────── */
export default function SubscriptionPage() {
  const { user } = useAuth();
  const toast = useToast();
  const isSuperAdmin = user?.role === "super_admin";

  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [subscriptions, setSubscriptions] = useState(null);

  useEffect(() => {
    if (isSuperAdmin) {
      api
        .get("/api/v1/fleets/subscriptions")
        .then(setSubscriptions)
        .catch((e) => {
          setError(e.message);
          toast.error(e.message);
        });
    } else {
      api
        .get("/api/v1/billing/overview")
        .then(setData)
        .catch((e) => {
          setError(e.message);
          toast.error(e.message);
        });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSuperAdmin]);

  async function handleAction(action, arg) {
    setBusy(action + (arg || ""));
    setError("");
    try {
      let res;
      if (action === "subscribe") {
        res = await api.post("/api/v1/billing/subscribe", { plan_code: arg });
      } else if (action === "renew") {
        res = await api.post(`/api/v1/billing/renew/${arg}`);
      } else if (action === "slot") {
        res = await api.post("/api/v1/billing/vehicle-slot", {});
      } else if (action === "adminRenew") {
        res = await api.post(`/api/v1/billing/renew/${arg.plan_code}`);
      }

      if (res?.redirect_url) {
        window.location.href = res.redirect_url;
      } else if (res?.trial) {
        toast.success("Trial activated!");
        if (!isSuperAdmin) {
          api.get("/api/v1/billing/overview").then(setData);
        }
      }
    } catch (e) {
      setError(e.message);
      toast.error(e.message);
    } finally {
      setBusy("");
    }
  }

  const fleet = data?.fleet;
  const plans = data?.plans || [];

  return (
    <div className="space-y-5">
      <div>
        <h2 className="page-title">Subscription</h2>
        <p className="page-sub">
          {isSuperAdmin
            ? "All fleet subscriptions with plan status and renewal options."
            : "Manage your plan, renew, and add extra vehicle slots."}
        </p>
      </div>
      {error && <div className="alert alert-error">{error}</div>}

      {isSuperAdmin ? (
        !subscriptions && !error ? (
          <Loader label="Loading subscriptions…" />
        ) : (
          <div className="card p-4">
            <AdminSubscriptionTable
              subscriptions={subscriptions}
              onRenew={(fleetId, planCode) =>
                handleAction("adminRenew", { fleet_id: fleetId, plan_code: planCode })
              }
            />
          </div>
        )
      ) : (
        <>
          {!data && !error && <Loader label="Loading subscription info…" />}
          {fleet && (
            <ManagerSubscription fleet={fleet} plans={plans} onAction={handleAction} />
          )}
        </>
      )}
    </div>
  );
}