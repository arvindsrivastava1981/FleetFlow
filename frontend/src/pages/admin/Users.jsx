import { useEffect, useState } from "react";
import { api } from "../../lib/api.js";

const ROLES = ["trip_manager", "driver"];
const ROLE_LABELS = { super_admin: "Super Admin", trip_manager: "Trip Manager", driver: "Driver" };
const emptyForm = { username: "", full_name: "", role: "trip_manager", phone: "", email: "", password: "" };

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);

  function load() {
    api
      .get("/api/v1/users")
      .then(setUsers)
      .catch((e) => setError(e.message));
  }
  useEffect(load, []);

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      if (editingId) {
        await api.put(`/api/v1/users/${editingId}`, form);
      } else {
        await api.post("/api/v1/users", form);
      }
      setForm(emptyForm);
      setEditingId(null);
      load();
    } catch (err) {
      setError(err.message);
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
    });
  }

  async function toggle(u) {
    try {
      await api.post(`/api/v1/users/${u.id}/toggle`, { activate: !u.is_active });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-extrabold text-slate-900">Manage Users</h2>
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <h3 className="text-sm font-extrabold text-slate-800 mb-3">
          {editingId ? "Edit User" : "Create New User"}
        </h3>
        <form onSubmit={onSubmit} className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <input value={form.username} onChange={(e) => set("username", e.target.value)} placeholder="Username" required disabled={!!editingId} className="border rounded-lg p-2 bg-slate-50 disabled:opacity-50" />
          <input value={form.full_name} onChange={(e) => set("full_name", e.target.value)} placeholder="Full Name" required className="border rounded-lg p-2 bg-slate-50" />
          <select value={form.role} onChange={(e) => set("role", e.target.value)} className="border rounded-lg p-2 bg-slate-50">
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
          <input value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="Phone" className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="Email" className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.password} onChange={(e) => set("password", e.target.value)} placeholder={editingId ? "Password (blank = keep)" : "Password"} required={!editingId} type="password" className="border rounded-lg p-2 bg-slate-50" />
          <div className="col-span-2 md:col-span-3 flex gap-2">
            <button type="submit" className="bg-sky-600 hover:bg-sky-700 text-white font-bold py-2 px-4 rounded-xl transition shadow">
              {editingId ? "Save Changes" : "Add User"}
            </button>
            {editingId && (
              <button type="button" onClick={() => { setForm(emptyForm); setEditingId(null); }} className="bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-2 px-4 rounded-xl">
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>
<div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
        <table className="w-full text-left">
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
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800">
                    {ROLE_LABELS[u.role] || u.role}
                  </span>
                </td>
                <td className="p-3 text-xs text-slate-600">{u.phone || "—"}</td>
                <td className="p-3 text-xs text-slate-600">{u.email || "—"}</td>
                <td className="p-3 text-xs flex gap-3">
                  <button onClick={() => startEdit(u)} className="text-sky-600 hover:text-sky-800 font-semibold">
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
    </div>
  );
}