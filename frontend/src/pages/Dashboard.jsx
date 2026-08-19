import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";

function StatCard({ label, head, sub, cls }) {
  return (
    <div className={`rounded-2xl p-5 shadow-sm ${cls || "bg-white"}`}>
      <p className="text-xs font-semibold uppercase opacity-80">{label}</p>
      <p className="text-2xl font-extrabold mt-1">{head}</p>
      {sub && <p className="text-[11px] mt-1 opacity-80">{sub}</p>}
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
    <div className="space-y-4">
      <h2 className="text-lg font-extrabold text-slate-900">My Dashboard</h2>
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">
          {error}
        </div>
      )}
      {!data && !error && (
        <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center text-sm text-slate-400">
          Loading dashboard…
        </div>
      )}

      {data?.role === "super_admin" && data.kpis && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Active Trips" head={data.kpis.active_trips} cls="bg-sky-50" />
          <StatCard label="Active Vehicles" head={data.kpis.active_vehicles} cls="bg-emerald-50" />
          <StatCard label="Active Drivers" head={data.kpis.active_drivers} cls="bg-amber-50" />
          <StatCard
            label="MTD Spend"
            head={`₹${(data.kpis.mtd_spend_total || 0).toLocaleString("en-IN")}`}
            cls="bg-slate-100"
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
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Active Dispatched" head={data.kpis.active_dispatched} cls="bg-sky-50" />
          <StatCard label="Pending Escalations" head={data.kpis.pending_escalations} cls="bg-amber-50" />
          <StatCard label="Advances Today" head={`₹${(data.kpis.advances_today || 0).toLocaleString("en-IN")}`} />
          <StatCard label="Awaiting Settlement" head={data.kpis.awaiting_settlement} cls="bg-emerald-50" />
        </div>
      )}

      {data?.role === "driver" && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <StatCard label="Today Logged" head={`₹${(data.today_logged || 0).toLocaleString("en-IN")}`} cls="bg-emerald-50" />
          <StatCard label="Cash in Hand" head={`₹${(data.cash_in_hand || 0).toLocaleString("en-IN")}`} cls="bg-sky-50" />
          {data.trip ? (
            <StatCard label="Active Trip" head={data.trip.trip_code} sub={data.trip.vehicle_no} cls="bg-slate-100" />
          ) : (
            <StatCard label="Active Trip" head="None" />
          )}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {(role === "trip_manager" || role === "super_admin") && (
          <Link
            to="/expenses"
            className="bg-sky-600 hover:bg-sky-500 text-white rounded-2xl p-5 text-center shadow-sm transition"
          >
            <span className="block text-2xl">🧾</span>
            <span className="text-xs font-bold block mt-2">Expense Ledger</span>
          </Link>
        )}
        {(role === "trip_manager" || role === "super_admin") && (
          <Link
            to="/trips"
            className="bg-slate-800 hover:bg-slate-700 text-white rounded-2xl p-5 text-center shadow-sm transition"
          >
            <span className="block text-2xl">🚚</span>
            <span className="text-xs font-bold block mt-2">Trips</span>
          </Link>
        )}
      </div>
    </div>
  );
}
