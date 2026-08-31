import { useEffect, useState } from "react";
import { api } from "../../lib/api.js";
import { useToast } from "../../context/ToastContext.jsx";
import Loader from "../../components/Loader.jsx";

const ROLES = ["trip_manager", "driver"];
const ROLE_LABELS = { super_admin: "Super Admin", trip_manager: "Trip Manager", driver: "Driver" };
const BATTA_UNIT = {
  FIXED_TRIP: "₹/trip",
  PER_KM: "₹/km",
  DAILY: "₹/day",
  NONE: "No batta",
};
const emptyForm = { email: "", full_name: "", role: "trip_manager", phone: "", password: "", fleet_id: "", batta_type: "FIXED_TRIP", default_batta_rate: "2500.00" };

function Required() {
  return <span className="text-rose-500 ml-0.5">*</span>;
}

export default function UsersPage() {
  const toast = useToast();
  const [users, setUsers] = useState([]);
  const [fleets, setFleets] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);

  function load() {
    api
      .get("/api/v1/users")
      .then(setUsers)
      .catch((e) => {
        setError(e.message);
        toast.error(e.message);
      })
      .finally(() => setLoading(false));
  }
  function loadFleets() {
    api.get("/api/v1/fleets").then(setFleets).catch(() => {});
  }
  useEffect(() => {
    load();
    loadFleets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (editingId) {
        await api.put(`/api/v1/users/${editingId}`, form);
        toast.success("User updated.");
      } else {
        await api.post("/api/v1/users", form);
        toast.success("User created.");
      }
      setForm(emptyForm);
      setEditingId(null);
      load();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  function startEdit(u) {
    setEditingId(u.id);
    setForm({
      email: u.email,
      full_name: u.full_name,
      role: u.role,
      phone: u.phone || "",
      password: "",
      fleet_id: u.fleet_id ? String(u.fleet_id) : "",
      batta_type: u.batta_type || "FIXED_TRIP",
      default_batta_rate: u.default_batta_rate != null ? String(u.default_batta_rate) : "2500.00",
    });
  }

  async function toggle(u) {
    try {
      await api.post(`/api/v1/users/${u.id}/toggle`, { activate: !u.is_active });
      toast.success(u.is_active ? "User deactivated." : "User activated.");
      load();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="page-title">Manage Users</h2>
        <p className="page-sub">All users in your fleet with their roles and status.</p>
      </div>
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      <div className="card-pad">
        <h3 className="text-sm font-extrabold text-slate-800 mb-3">
          {editingId ? "Edit User" : "Create New User"}
        </h3>
        <form
          onSubmit={onSubmit}
          className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3"
        >
          {/* Email */}
          <div>
            <label className="label" htmlFor="email">
              Email <Required />
            </label>
            <input
              id="email"
              type="email"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
              placeholder="e.g. ramesh@fleet.com"
              required
              disabled={!!editingId}
              className="input disabled:opacity-50"
            />
          </div>

          {/* Full Name */}
          <div>
            <label className="label" htmlFor="full_name">
              Full Name <Required />
            </label>
            <input
              id="full_name"
              value={form.full_name}
              onChange={(e) => set("full_name", e.target.value)}
              placeholder="e.g. Ramesh Kumar"
              required
              className="input"
            />
          </div>

          {/* Role */}
          <div>
            <label className="label" htmlFor="role">
              Role <Required />
            </label>
            <select
              id="role"
              value={form.role}
              onChange={(e) => set("role", e.target.value)}
              className="input"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {ROLE_LABELS[r]}
                </option>
              ))}
            </select>
          </div>

          {/* Fleet (trip_manager only) */}
          {form.role === "trip_manager" && (
            <div>
              <label className="label" htmlFor="fleet_id">Default Fleet</label>
              <select
                id="fleet_id"
                value={form.fleet_id}
                onChange={(e) => set("fleet_id", e.target.value)}
                className="input"
              >
                <option value="">Select fleet…</option>
                {fleets.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.owner_name} — {f.plan_name || f.plan_code || "fleet"}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Phone */}
          <div>
            <label className="label" htmlFor="phone">Phone</label>
            <input
              id="phone"
              value={form.phone}
              onChange={(e) => set("phone", e.target.value)}
              placeholder="e.g. +919876543210"
              className="input"
            />
          </div>

          {/* Salary Type (driver only) */}
          {form.role === "driver" && (
            <>
              <div>
                <label className="label" htmlFor="batta_type">
                  Salary Type <Required />
                </label>
                <select
                  id="batta_type"
                  value={form.batta_type}
                  onChange={(e) => set("batta_type", e.target.value)}
                  className="input"
                >
                  {["FIXED_TRIP", "PER_KM", "DAILY", "NONE"].map((bt) => (
                    <option key={bt} value={bt}>{bt.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label" htmlFor="default_batta_rate">
                  Salary Rate ({BATTA_UNIT[form.batta_type] || ""}){" "}
                  {form.batta_type !== "NONE" && <Required />}
                </label>
                <input
                  id="default_batta_rate"
                  value={form.default_batta_rate}
                  onChange={(e) => set("default_batta_rate", e.target.value)}
                  placeholder="e.g. 2500.00"
                  type="number"
                  step="any"
                  min="0"
                  disabled={form.batta_type === "NONE"}
                  className="input disabled:opacity-50"
                />
              </div>
            </>
          )}

          {/* Password */}
          <div>
            <label className="label" htmlFor="password">
              Password {editingId ? "" : <Required />}
            </label>
            <input
              id="password"
              value={form.password}
              onChange={(e) => set("password", e.target.value)}
              placeholder={editingId ? "Leave blank to keep current" : "Set login password"}
              required={!editingId}
              type="password"
              className="input"
            />
          </div>

          {/* Actions */}
          <div className="sm:col-span-2 lg:col-span-3 flex gap-2">
            <button type="submit" disabled={busy} className="btn-primary">
              {busy ? "Saving…" : editingId ? "Save Changes" : "Add User"}
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
        <Loader label="Loading users…" />
      ) : (
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Name</th>
              <th>Role</th>
              <th>Phone</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td className="font-semibold text-ink-800">{u.email}</td>
                <td>{u.full_name}</td>
                <td>
                  <span className="badge badge-info">
                    {ROLE_LABELS[u.role] || u.role}
                  </span>
                </td>
                <td>{u.phone || "—"}</td>
                <td>
                  <span className={`badge ${u.is_active ? "badge-success" : "badge-danger"}`}>
                    {u.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  <div className="flex gap-3 text-sm font-semibold">
                    <button onClick={() => startEdit(u)} className="text-brand-600 hover:text-brand-800">
                      Edit
                    </button>
                    <button onClick={() => toggle(u)} className={u.is_active ? "text-rose-600 hover:text-rose-800" : "text-emerald-600 hover:text-emerald-800"}>
                      {u.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!users.length && (
              <tr>
                <td colSpan="6" className="empty">
                  No users yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      )}
    </div>
  );
}