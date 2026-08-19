import { useEffect, useState } from "react";
import { api } from "../lib/api.js";

// Aligned with users.batta_type CHECK (FIXED_TRIP/PER_KM/DAILY/NONE).
const BATTA_TYPES = ["FIXED_TRIP", "PER_KM", "DAILY", "NONE"];
const BATTA_UNIT = {
  FIXED_TRIP: "₹/trip",
  PER_KM: "₹/km",
  DAILY: "₹/day",
  NONE: "No batta",
};
const emptyForm = {
  username: "",
  full_name: "",
  phone: "",
  email: "",
  password: "",
  batta_type: "FIXED_TRIP",
  default_batta_rate: "2500.00",
};

export default function DriversPage() {
  const [drivers, setDrivers] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);

  function load() {
    api
      .get("/api/v1/drivers")
      .then(setDrivers)
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
        const { username, ...payload } = form; // username is immutable on edit
        await api.put(`/api/v1/drivers/${editingId}`, payload);
      } else {
        await api.post("/api/v1/drivers", form);
      }
      setForm(emptyForm);
      setEditingId(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  function startEdit(d) {
    setEditingId(d.id);
    setForm({
      username: d.username,
      full_name: d.full_name,
      phone: d.phone || "",
      email: d.email || "",
      password: "",
      batta_type: d.batta_type || "FIXED_TRIP",
      default_batta_rate: d.default_batta_rate != null ? String(d.default_batta_rate) : "2500.00",
    });
  }

  async function toggle(d) {
    try {
      await api.post(`/api/v1/drivers/${d.id}/toggle`, { activate: !d.is_active });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="page-title">Drivers</h2>
        <p className="text-xs text-slate-500">Registered driver users and their batta profile.</p>
      </div>
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}
      <div className="card-pad">
        <h3 className="text-sm font-extrabold text-slate-800 mb-3">
          {editingId ? "Edit Driver" : "Add New Driver"}
        </h3>
        <form onSubmit={onSubmit} className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <input
            value={form.username}
            onChange={(e) => set("username", e.target.value)}
            placeholder="Username"
            required
            disabled={!!editingId}
            className="input disabled:opacity-50"
          />
          <input
            value={form.full_name}
            onChange={(e) => set("full_name", e.target.value)}
            placeholder="Full Name"
            required
            className="input"
          />
          <input
            value={form.phone}
            onChange={(e) => set("phone", e.target.value)}
            placeholder="Phone (+91...)"
            className="input"
          />
          <input
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            placeholder="Email"
            type="email"
            className="input"
          />
          <input
            value={form.password}
            onChange={(e) => set("password", e.target.value)}
            placeholder={editingId ? "Password (blank = keep)" : "Password"}
            required={!editingId}
            type="password"
            className="input"
          />
          <select
            value={form.batta_type}
            onChange={(e) => set("batta_type", e.target.value)}
            className="input"
          >
            {BATTA_TYPES.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
          <input
            value={form.default_batta_rate}
            onChange={(e) => set("default_batta_rate", e.target.value)}
            placeholder={`Batta Rate (${BATTA_UNIT[form.batta_type] || "₹/trip"})`}
            type="number"
            step="0.01"
            min="0"
            disabled={form.batta_type === "NONE"}
            className="input disabled:opacity-50"
          />
          <div className="col-span-2 md:col-span-3 flex gap-2">
            <button type="submit" className="btn-primary py-2 px-4 rounded-xl transition shadow">
              {editingId ? "Save Changes" : "Add Driver"}
            </button>
            {editingId && (
              <button
                type="button"
                onClick={() => { setForm(emptyForm); setEditingId(null); }}
                className="btn-secondary py-2 px-4 rounded-xl"
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Username</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Name</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Batta Type</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Batta Rate</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Phone</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Status</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody>
            {drivers.map((d) => (
              <tr key={d.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-3 text-xs font-bold text-slate-800">{d.username}</td>
                <td className="p-3 text-xs text-slate-600">{d.full_name}</td>
                <td className="p-3 text-xs text-slate-600">
                  {d.batta_type === "NONE" ? (
                    <span className="text-slate-400">—</span>
                  ) : (
                    d.batta_type || "FIXED_TRIP"
                  )}
                </td>
                <td className={`p-3 text-xs font-semibold ${d.batta_type === "NONE" ? "text-slate-400" : "text-emerald-700"}`}>
                  {d.batta_type === "NONE"
                    ? "—"
                    : `₹${(Number(d.default_batta_rate) || 0).toLocaleString("en-IN")}`}
                </td>
                <td className="p-3 text-xs text-slate-600">{d.phone || "—"}</td>
                <td className="p-3 text-xs">
                  <span
                    className={`badge ${
                      d.is_active
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-rose-100 text-rose-800"
                    }`}
                  >
                    {d.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="p-3 text-xs flex gap-3">
                  <button onClick={() => startEdit(d)} className="text-brand-600 hover:text-brand-800 font-semibold">
                    Edit
                  </button>
                  <button
                    onClick={() => toggle(d)}
                    className={d.is_active ? "text-rose-600 hover:text-rose-800 font-semibold" : "text-emerald-600 hover:text-emerald-800 font-semibold"}
                  >
                    {d.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
            {!drivers.length && (
              <tr>
                <td colSpan="7" className="p-6 text-center text-xs text-slate-400">
                  No drivers yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}