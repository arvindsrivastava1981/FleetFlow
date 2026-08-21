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
const emptyForm = { username: "", full_name: "", role: "trip_manager", phone: "", email: "", password: "", fleet_id: "", batta_type: "FIXED_TRIP", default_batta_rate: "2500.00" };

export default function UsersPage() {
  const toast = useToast();
  const [users, setUsers] = useState([]);
  const [fleets, setFleets] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);

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
    }
  }

  function startEdit(u) {
    setEditingId(u.id);
    setForm({
      username: u.username,
      full_name: u.full_name,
      role: u.role,
      phone: u.phone || "",
      email: u.email || "",
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
      <h2 className="page-title">Manage Users</h2>
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      <div className="card-pad">
        <h3 className="text-sm font-extrabold text-slate-800 mb-3">
          {editingId ? "Edit User" : "Create New User"}
        </h3>
        <form onSubmit={onSubmit} className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <input value={form.username} onChange={(e) => set("username", e.target.value)} placeholder="Username" required disabled={!!editingId} className="input disabled:opacity-50" />
          <input value={form.full_name} onChange={(e) => set("full_name", e.target.value)} placeholder="Full Name" required className="input" />
          <select value={form.role} onChange={(e) => set("role", e.target.value)} className="input">
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
          {form.role === "trip_manager" && (
            <select value={form.fleet_id} onChange={(e) => set("fleet_id", e.target.value)} className="input">
              <option value="">Default Fleet</option>
              {fleets.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.owner_name} — {f.plan_name || f.plan_code || "fleet"}
                </option>
              ))}
            </select>
          )}
          <input value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="Phone" className="input" />
          <input value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="Email" className="input" />
          {form.role === "driver" && (
            <>
              <select value={form.batta_type} onChange={(e) => set("batta_type", e.target.value)} className="input">
                {["FIXED_TRIP", "PER_KM", "DAILY", "NONE"].map((bt) => (
                  <option key={bt} value={bt}>{bt.replace(/_/g, " ")}</option>
                ))}
              </select>
              <input value={form.default_batta_rate} onChange={(e) => set("default_batta_rate", e.target.value)} placeholder={`Batta Rate ${BATTA_UNIT[form.batta_type] || ""}`} type="number" step="any" min="0" disabled={form.batta_type === "NONE"} className="input disabled:opacity-50" />
            </>
          )}
          <input value={form.password} onChange={(e) => set("password", e.target.value)} placeholder={editingId ? "Password (blank = keep)" : "Password"} required={!editingId} type="password" className="input" />
          <div className="col-span-2 md:col-span-3 flex gap-2">
            <button type="submit" className="btn-primary py-2 px-4 rounded-xl transition shadow">
              {editingId ? "Save Changes" : "Add User"}
            </button>
            {editingId && (
              <button type="button" onClick={() => { setForm(emptyForm); setEditingId(null); }} className="btn-secondary py-2 px-4 rounded-xl">
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
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Username</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Name</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Role</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Phone</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Email</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-3 text-xs font-bold text-slate-800">{u.username}</td>
                <td className="p-3 text-xs text-slate-600">{u.full_name}</td>
                <td className="p-3 text-xs">
                  <span className="badge badge-info">
                    {ROLE_LABELS[u.role] || u.role}
                  </span>
                </td>
                <td className="p-3 text-xs text-slate-600">{u.phone || "—"}</td>
                <td className="p-3 text-xs text-slate-600">{u.email || "—"}</td>
                <td className="p-3 text-xs flex gap-3">
                  <button onClick={() => startEdit(u)} className="text-brand-600 hover:text-brand-800 font-semibold">
                    Edit
                  </button>
                  <button onClick={() => toggle(u)} className={u.is_active ? "text-rose-600 hover:text-rose-800 font-semibold" : "text-emerald-600 hover:text-emerald-800 font-semibold"}>
                    {u.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
            {!users.length && (
              <tr>
                <td colSpan="6" className="p-6 text-center text-xs text-slate-400">
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