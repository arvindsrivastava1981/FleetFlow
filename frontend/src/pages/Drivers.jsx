import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { useToast } from "../context/ToastContext.jsx";
import Loader from "../components/Loader.jsx";

// Aligned with users.batta_type CHECK (FIXED_TRIP/PER_KM/DAILY/NONE).
const BATTA_TYPES = ["FIXED_TRIP", "PER_KM", "DAILY", "NONE"];
const BATTA_UNIT = {
  FIXED_TRIP: "₹/trip",
  PER_KM: "₹/km",
  DAILY: "₹/day",
  NONE: "No batta",
};
const emptyForm = {
  email: "",
  full_name: "",
  phone: "",
  password: "",
  batta_type: "FIXED_TRIP",
  default_batta_rate: "2500.00",
  licence_expiry: "",
};

function Required() {
  return <span className="text-rose-500 ml-0.5">*</span>;
}

export default function DriversPage() {
  const toast = useToast();
  const [drivers, setDrivers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);

  function load() {
    api
      .get("/api/v1/drivers")
      .then(setDrivers)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (editingId) {
        const { email, ...payload } = form;
        await api.put(`/api/v1/drivers/${editingId}`, payload);
        toast.success("Driver updated successfully.");
      } else {
        await api.post("/api/v1/drivers", form);
        toast.success("Driver added successfully.");
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

  function startEdit(d) {
    setEditingId(d.id);
    setForm({
      email: d.email,
      full_name: d.full_name,
      phone: d.phone || "",
      password: "",
      batta_type: d.batta_type || "FIXED_TRIP",
      default_batta_rate: d.default_batta_rate != null ? String(d.default_batta_rate) : "2500.00",
      licence_expiry: d.licence_expiry ? String(d.licence_expiry).slice(0, 10) : "",
    });
  }

  async function toggle(d) {
    try {
      await api.post(`/api/v1/drivers/${d.id}/toggle`, { activate: !d.is_active });
      toast.success(
        d.is_active ? "Driver deactivated." : "Driver activated."
      );
      load();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="page-title">Drivers</h2>
        <p className="page-sub">Registered driver users and their batta profile.</p>
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
        <form
          onSubmit={onSubmit}
          className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3"
        >
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

          {/* Email */}
          <div>
            <label className="label" htmlFor="email">
              Email <Required />
            </label>
            <input
              id="email"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
              placeholder="e.g. ramesh@fleet.com"
              type="email"
              required
              className="input"
            />
          </div>

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

          {/* Salary Type */}
          <div>
            <label className="label" htmlFor="batta_type">Salary Type <Required /></label>
            <select
              id="batta_type"
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
          </div>

          {/* Salary Rate */}
          <div>
            <label className="label" htmlFor="default_batta_rate">
              Salary Rate ({BATTA_UNIT[form.batta_type] || "₹/trip"}){" "}
              {form.batta_type !== "NONE" && <Required />}
            </label>
            <input
              id="default_batta_rate"
              value={form.default_batta_rate}
              onChange={(e) => set("default_batta_rate", e.target.value)}
              placeholder="e.g. 2500.00"
              type="number"
              step="0.01"
              min="0"
              disabled={form.batta_type === "NONE"}
              className="input disabled:opacity-50"
            />
          </div>

          {/* Licence Expiry */}
          <div>
            <label className="label" htmlFor="licence_expiry">Licence Expiry</label>
            <input
              id="licence_expiry"
              type="date"
              value={form.licence_expiry}
              onChange={(e) => set("licence_expiry", e.target.value)}
              className="input"
            />
          </div>

          {/* Actions */}
          <div className="sm:col-span-2 lg:col-span-3 flex gap-2">
            <button type="submit" disabled={busy} className="btn-primary">
              {busy ? "Saving…" : editingId ? "Save Changes" : "Add Driver"}
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
        <Loader label="Loading drivers…" />
      ) : (
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Name</th>
              <th>Salary Type</th>
              <th>Salary Rate</th>
              <th>Phone</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {drivers.map((d) => (
              <tr key={d.id}>
                <td className="font-semibold text-ink-800">{d.email}</td>
                <td>
                  {d.full_name}
                  {d.licence_expiry && new Date(d.licence_expiry) <= new Date(Date.now() + 14 * 864e5) && (
                    <span
                      className="badge badge-danger ml-1"
                      title={`Licence expires ${d.licence_expiry}`}
                    >
                      licence ⚠
                    </span>
                  )}
                </td>
                <td>
                  {d.batta_type === "NONE" ? (
                    <span className="text-ink-400">—</span>
                  ) : (
                    d.batta_type || "FIXED_TRIP"
                  )}
                </td>
                <td className={d.batta_type === "NONE" ? "text-ink-400" : "font-semibold text-emerald-700"}>
                  {d.batta_type === "NONE"
                    ? "—"
                    : `₹${(Number(d.default_batta_rate) || 0).toLocaleString("en-IN")} ${BATTA_UNIT[d.batta_type] || BATTA_UNIT.FIXED_TRIP}`}
                </td>
                <td>{d.phone || "—"}</td>
                <td>
                  <span className={`badge ${d.is_active ? "badge-success" : "badge-danger"}`}>
                    {d.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  <div className="flex gap-3 text-sm font-semibold">
                    <button onClick={() => startEdit(d)} className="text-brand-600 hover:text-brand-800">
                      Edit
                    </button>
                    <button
                      onClick={() => toggle(d)}
                      className={d.is_active ? "text-rose-600 hover:text-rose-800" : "text-emerald-600 hover:text-emerald-800"}
                    >
                      {d.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!drivers.length && (
              <tr>
                <td colSpan="7" className="empty">
                  No drivers yet.
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