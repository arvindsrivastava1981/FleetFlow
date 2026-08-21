import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";

const ic = (n) => `₹${(Number(n) || 0).toLocaleString("en-IN")}`;

function KpiCard({ icon, label, value, sub, accent, chip }) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-ink-200 bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:shadow-cardHover">
      <div className={`absolute inset-x-0 top-0 h-1 ${accent || "bg-brand-600"}`} />
      <div className="flex items-center justify-between gap-3">
        <p className="stat-label">{label}</p>
        <span
          className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg text-lg ${chip || "bg-brand-50 text-brand-600"}`}
        >
          {icon}
        </span>
      </div>
      <p className="mt-2 text-2xl font-extrabold tracking-tight text-ink-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-ink-500">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/v1/dashboard/overview")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  const role = user?.role;
  const firstName = user?.full_name ? user.full_name.split(" ")[0] : user?.username || "there";

  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 17) return "Good afternoon";
    return "Good evening";
  })();

  return (
    <div className="space-y-6">
      {/* Welcome hero banner */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-700 via-brand-600 to-brand-500 p-6 text-white shadow-card sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-white/10 blur-2xl" />
        <div className="pointer-events-none absolute right-24 -bottom-20 h-40 w-40 rounded-full bg-white/10 blur-2xl" />
        <div className="relative">
          <p className="text-xs font-bold uppercase tracking-wider text-brand-100">
            {role === "super_admin"
              ? "Fleet-wide control"
              : role === "trip_manager"
              ? "Dispatch &amp; settlement"
              : "Your trip at a glance"}
          </p>
          <h2 className="mt-1 text-2xl font-extrabold tracking-tight sm:text-3xl">
            {greeting}, {firstName} 👋
          </h2>
          <p className="mt-1 max-w-xl text-sm text-brand-50/90 sm:text-base">
            {role === "super_admin"
              ? "Here is your entire fleet at a glance — trips, vehicles, spend and leakage."
              : role === "trip_manager"
              ? "Monitor your live dispatches, advances and escalations in one place."
              : "Track today's logged spend and your cash in hand, all in real time."}
          </p>
        </div>
      </section>

      {data?.role === "super_admin" && data.kpis && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard icon="🚚" label="Active Trips" value={data.kpis.active_trips} accent="bg-brand-600" chip="bg-brand-50 text-brand-600" />
            <KpiCard icon="🚛" label="Active Vehicles" value={data.kpis.active_vehicles} accent="bg-emerald-500" chip="bg-emerald-50 text-emerald-600" />
            <KpiCard icon="👥" label="Active Drivers" value={data.kpis.active_drivers} accent="bg-amber-500" chip="bg-amber-50 text-amber-600" />
            <KpiCard icon="💳" label="MTD Spend" value={ic(data.kpis.mtd_spend_total)} sub="This month" accent="bg-ink-700" chip="bg-ink-100 text-ink-700" />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <KpiCard icon="🛡️" label="Leakage Prevented" value={ic(data.kpis.leakage_prevented)} sub="Flagged claims rejected" accent="bg-emerald-500" chip="bg-emerald-50 text-emerald-600" />
            <KpiCard icon="🧰" label="Outstanding Float" value={ic(data.kpis.outstanding_float)} sub="Cash in the field" accent="bg-rose-500" chip="bg-rose-50 text-rose-600" />
            <div className="flex flex-col justify-center rounded-xl border border-dashed border-brand-300 bg-brand-50/60 p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-brand-700/70">Quick access</p>
              <p className="mt-1 text-sm text-brand-800/80">
                Dispatch new trips, review vehicles and manage drivers from the sidebar.
              </p>
            </div>
          </div>
        </>
      )}

      {data?.role === "trip_manager" && data.kpis && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KpiCard icon="📤" label="Active Dispatched" value={data.kpis.active_dispatched} accent="bg-brand-600" chip="bg-brand-50 text-brand-600" />
            <KpiCard icon="🔔" label="Pending Escalations" value={data.kpis.pending_escalations} accent="bg-amber-500" chip="bg-amber-50 text-amber-600" />
            <KpiCard icon="💵" label="Advances Today" value={ic(data.kpis.advances_today)} accent="bg-emerald-500" chip="bg-emerald-50 text-emerald-600" />
            <KpiCard icon="🤝" label="Awaiting Settlement" value={data.kpis.awaiting_settlement} accent="bg-sky-500" chip="bg-sky-50 text-sky-600" />
          </div>
{(data.active_trips || []).length > 0 ? (
            <section className="card overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-200 px-5 py-4">
                <div>
                  <h3 className="text-base font-bold text-ink-900">Live Dispatches</h3>
                  <p className="text-xs text-ink-500">Real-time status of your active trips.</p>
                </div>
                <Link to="/trips" className="btn-secondary btn-sm">View all →</Link>
              </div>
              <ul className="divide-y divide-ink-100">
                {data.active_trips.map((t) => (
                  <li key={t.trip_code}>
                    <Link to={`/trips/${t.trip_code}`} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-5 py-4 transition hover:bg-ink-50/70">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-bold text-ink-900">{t.trip_code}</span>
                          <span className="badge badge-success">ACTIVE</span>
                          {t.pending_n > 0 && <span className="badge badge-warning">{t.pending_n} pending</span>}
                        </div>
                        <p className="mt-0.5 truncate text-sm text-ink-500">{t.vehicle_no} · {t.driver_name}</p>
                        {t.current_odo != null && (
                          <p className="mt-0.5 text-xs text-ink-400">ODO {Number(t.current_odo).toLocaleString("en-IN")} km</p>
                        )}
                      </div>
                      <div className="text-left sm:text-right">
                        <p className="font-extrabold text-ink-900">{ic(t.claimed)}</p>
                        <p className="text-xs text-ink-400">claimed</p>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ) : (
            <section className="card flex flex-col items-center gap-2 p-10 text-center">
              <span className="text-3xl">📭</span>
              <p className="font-medium text-ink-700">No active trips right now</p>
              <p className="text-sm text-ink-500">Start a new dispatch, or take a breather — nothing needs attention.</p>
              <Link to="/trips/new" className="btn-primary mt-1">+ Start New Trip</Link>
            </section>
          )}
        </>
      )}

      {data?.role === "driver" && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            <KpiCard icon="🧾" label="Today Logged" value={ic(data.today_logged)} accent="bg-emerald-500" chip="bg-emerald-50 text-emerald-600" />
            <KpiCard icon="💵" label="Cash in Hand" value={ic(data.cash_in_hand)} accent="bg-brand-600" chip="bg-brand-50 text-brand-600" />
            {data.trip ? (
              <KpiCard icon="🚚" label="Active Trip" value={data.trip.trip_code} sub={data.trip.vehicle_no} accent="bg-amber-500" chip="bg-amber-50 text-amber-600" />
            ) : (
              <div className="col-span-2 flex flex-col justify-center rounded-xl border border-dashed border-ink-300 bg-white p-5 lg:col-span-1">
                <p className="stat-label">Active Trip</p>
                <p className="mt-2 text-2xl font-extrabold tracking-tight text-ink-300">None</p>
                <p className="mt-1 text-xs text-ink-500">No dispatch assigned to you.</p>
              </div>
            )}
          </div>
          {data.trip && (
            <section className="card p-5">
              <h3 className="text-base font-bold text-ink-900">Quick actions</h3>
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Link to="/whatsapp-driver" className="btn-primary">💬 Send receipt via WhatsApp</Link>
                <Link to={`/trips/${data.trip.trip_code}`} className="btn-secondary">View trip details</Link>
              </div>
            </section>
          )}
        </>
      )}

      </div>
  );
}
