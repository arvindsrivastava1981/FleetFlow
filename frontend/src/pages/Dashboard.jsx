import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";

function StatCard({ label, head, sub, cls }) {
  return (
    <div className={`stat ${cls || "bg-white"}`}>
      <p className={`stat-label ${cls ? "opacity-80" : "text-ink-400"}`}>
        {label}
      </p>
      <p className="stat-value">{head}</p>
      {sub && <p className="stat-sub">{sub}</p>}
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

  return (
    <div className="space-y-6">
      <div className="page-head">
        <div>
          <h2 className="page-title">My Dashboard</h2>
          <p className="page-sub">
            Welcome back — here is your fleet at a glance.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {!data && !error && (
        <div className="card p-10 text-center text-sm text-ink-400">
          <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-ink-200 border-t-brand-600" />
          <p className="mt-3">Loading dashboard…</p>
        </div>
      )}

      {data?.role === "super_admin" && data.kpis && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatCard label="Active Trips" head={data.kpis.active_trips} cls="bg-brand-50" />
          <StatCard label="Active Vehicles" head={data.kpis.active_vehicles} cls="bg-emerald-50" />
          <StatCard label="Active Drivers" head={data.kpis.active_drivers} cls="bg-amber-50" />
          <StatCard
            label="MTD Spend"
            head={`₹${(data.kpis.mtd_spend_total || 0).toLocaleString("en-IN")}`}
            cls="bg-ink-100"
          />
          <StatCard
            label="Leakage Prevented"
            head={`₹${(data.kpis.leakage_prevented || 0).toLocaleString("en-IN")}`}
          />
          <StatCard
            label="Outstanding Float"
            head={`₹${(data.kpis.outstanding_float || 0).toLocaleString("en-IN")}`}
          />
        </div>
      )}

      {data?.role === "trip_manager" && data.kpis && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatCard label="Active Dispatched" head={data.kpis.active_dispatched} cls="bg-brand-50" />
          <StatCard label="Pending Escalations" head={data.kpis.pending_escalations} cls="bg-amber-50" />
          <StatCard label="Advances Today" head={`₹${(data.kpis.advances_today || 0).toLocaleString("en-IN")}`} />
          <StatCard label="Awaiting Settlement" head={data.kpis.awaiting_settlement} cls="bg-emerald-50" />
        </div>
      )}

      {data?.role === "driver" && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <StatCard label="Today Logged" head={`₹${(data.today_logged || 0).toLocaleString("en-IN")}`} cls="bg-emerald-50" />
          <StatCard label="Cash in Hand" head={`₹${(data.cash_in_hand || 0).toLocaleString("en-IN")}`} cls="bg-brand-50" />
          {data.trip ? (
            <StatCard label="Active Trip" head={data.trip.trip_code} sub={data.trip.vehicle_no} cls="bg-ink-100" />
          ) : (
            <StatCard label="Active Trip" head="None" />
          )}
        </div>
      )}

      {(role === "trip_manager" || role === "super_admin") && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Link
            to="/expenses"
            className="flex flex-col items-center justify-center gap-2 rounded-xl bg-brand-600 p-5 text-center text-white shadow-sm transition hover:bg-brand-700"
          >
            <span className="text-2xl">🧾</span>
            <span className="text-xs font-semibold">Expense Ledger</span>
          </Link>
          <Link
            to="/trips"
            className="flex flex-col items-center justify-center gap-2 rounded-xl bg-ink-800 p-5 text-center text-white shadow-sm transition hover:bg-ink-900"
          >
            <span className="text-2xl">🚚</span>
            <span className="text-xs font-semibold">Active Trips</span>
          </Link>
        </div>
      )}
    </div>
  );
}
