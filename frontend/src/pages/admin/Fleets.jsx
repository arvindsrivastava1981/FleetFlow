import { useEffect, useState } from "react";
import { api } from "../../lib/api.js";
import { useAuth } from "../../context/AuthContext.jsx";
import { useToast } from "../../context/ToastContext.jsx";
import Loader from "../../components/Loader.jsx";

const emptyForm = { owner_name: "", phone: "", email: "", subscription_plan: "MONTHLY" };

function Required() {
  return <span className="text-rose-500 ml-0.5">*</span>;
}

export default function FleetsPage() {
  const { user } = useAuth();
  const toast = useToast();
  const isSuperAdmin = user?.role === "super_admin";
  const [fleets, setFleets] = useState([]);
  const [plans, setPlans] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);

  function load() {
    api
      .get("/api/v1/fleets")
      .then(setFleets)
      .catch((e) => {
        setError(e.message);
        toast.error(e.message);
      })
      .finally(() => setLoading(false));
  }
  function loadPlans() {
    api.get("/api/v1/fleets/plans").then(setPlans).catch(() => {});
  }
  useEffect(() => {
    load();
    loadPlans();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const payload = { ...form, email: form.email || null };
      if (editingId) {
        await api.put(`/api/v1/fleets/${editingId}`, payload);
        toast.success("Fleet updated.");
      } else {
        await api.post("/api/v1/fleets", payload);
        toast.success("Fleet created.");
      }
      setForm(emptyForm);
      setEditingId(null);
      load();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  }

  function startEdit(f) {
    setEditingId(f.id);
    setForm({
      owner_name: f.owner_name,
      phone: f.phone,
      email: f.email || "",
      subscription_plan: f.plan_code || "MONTHLY",
    });
  }

  async function toggle(f) {
    try {
      await api.post(`/api/v1/fleets/${f.id}/toggle`, { activate: !f.is_active });
      toast.success(f.is_active ? "Fleet deactivated." : "Fleet activated.");
      load();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  }

  const statusCls = (s) =>
    ({ TRIAL: "badge-info", ACTIVE: "bg-emerald-100 text-emerald-800", PAST_DUE: "bg-amber-100 text-amber-800", CANCELLED: "bg-rose-100 text-rose-800" }[s] || "bg-slate-100 text-slate-600");

  return (
    <div className="space-y-5">
      <div>
        <h2 className="page-title">Manage Fleets</h2>
        <p className="page-sub">Create and manage transport firms.</p>
      </div>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card-pad">
        <h3 className="mb-3 text-sm font-bold text-ink-800">
          {editingId ? "Edit Fleet" : "Create New Fleet"}
        </h3>
        {!isSuperAdmin && !editingId && (
          <p className="mb-2 text-sm text-brand-700">
            Creating a fleet makes it your active fleet — new vehicles you add will belong to it.
          </p>
        )}
        <form
          onSubmit={onSubmit}
          className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4"
        >
          {/* Owner Name */}
          <div>
            <label className="label" htmlFor="owner_name">
              Owner Name <Required />
            </label>
            <input
              id="owner_name"
              value={form.owner_name}
              onChange={(e) => set("owner_name", e.target.value)}
              placeholder="e.g. Sharma Transports"
              required
              className="input"
            />
          </div>

          {/* Phone */}
          <div>
            <label className="label" htmlFor="phone">
              Phone <Required />
            </label>
            <input
              id="phone"
              value={form.phone}
              onChange={(e) => set("phone", e.target.value)}
              placeholder="e.g. +919876543210"
              required
              className="input"
            />
          </div>

          {/* Email */}
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
              placeholder="e.g. owner@firm.com"
              className="input"
            />
          </div>

          {/* Subscription Plan */}
          <div>
            <label className="label" htmlFor="subscription_plan">
              Subscription Plan <Required />
            </label>
            <select
              id="subscription_plan"
              value={form.subscription_plan}
              onChange={(e) => set("subscription_plan", e.target.value)}
              className="input"
              disabled={!!editingId}
            >
              {plans
                .filter((p) => p.code !== "TRIAL")
                .map((p) => (
                  <option key={p.code} value={p.code}>
                    {p.name} (₹{p.price})
                  </option>
                ))}
            </select>
          </div>

          {/* Actions */}
          <div className="sm:col-span-2 lg:col-span-4 flex gap-2">
            <button type="submit" className="btn-primary">
              {editingId ? "Save Changes" : "Create Fleet"}
            </button>
            {editingId && (
              <button
                type="button"
                onClick={() => { setForm(emptyForm); setEditingId(null); setError(""); }}
                className="btn-secondary"
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      {loading ? (
        <Loader label="Loading fleets…" />
      ) : (
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Owner</th>
              <th>Phone</th>
              <th>Plan</th>
              <th>Status</th>
              <th>Vehicles</th>
              {isSuperAdmin && <th>Action</th>}
            </tr>
          </thead>
          <tbody>
            {fleets.map((f) => (
              <tr key={f.id}>
                <td className="font-semibold text-ink-800">{f.owner_name}</td>
                <td>{f.phone}</td>
                <td>{f.plan_name || "—"}</td>
                <td>
                  <span className={`badge ${statusCls(f.subscription_status)}`}>
                    {(f.subscription_status || "TRIAL").replace("_", " ")}
                  </span>
                </td>
                <td>{f.vehicle_count} / {f.vehicle_limit}</td>
                <td>
                  <div className="flex gap-3 text-sm font-semibold">
                    {isSuperAdmin && (
                      <>
                        <button onClick={() => startEdit(f)} className="text-brand-600 hover:text-brand-800">Edit</button>
                        <button onClick={() => toggle(f)} className={f.is_active ? "text-rose-600 hover:text-rose-800" : "text-emerald-600 hover:text-emerald-800"}>
                          {f.is_active ? "Deactivate" : "Activate"}
                        </button>
                      </>
                    )}
                    {!isSuperAdmin && <span className="text-ink-400">Read-only</span>}
                  </div>
                </td>
              </tr>
            ))}
            {!fleets.length && (
              <tr>
                <td colSpan="6" className="empty">No fleets yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      )}
    </div>
  );
}