import { useEffect, useState } from "react";
import { api } from "../../lib/api.js";

const emptyForm = { owner_name: "", phone: "", email: "", subscription_plan: "MONTHLY" };

export default function FleetsPage() {
  const [fleets, setFleets] = useState([]);
  const [plans, setPlans] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);

  function load() {
    api.get("/api/v1/fleets").then(setFleets).catch((e) => setError(e.message));
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
      } else {
        await api.post("/api/v1/fleets", payload);
      }
      setForm(emptyForm);
      setEditingId(null);
      load();
    } catch (err) {
      setError(err.message);
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
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  const statusCls = (s) =>
    ({ TRIAL: "bg-sky-100 text-sky-800", ACTIVE: "bg-emerald-100 text-emerald-800", PAST_DUE: "bg-amber-100 text-amber-800", CANCELLED: "bg-rose-100 text-rose-800" }[s] || "bg-slate-100 text-slate-600");

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-extrabold text-slate-900">Manage Fleets</h2>
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <h3 className="text-sm font-extrabold text-slate-800 mb-3">
          {editingId ? "Edit Fleet" : "Create New Fleet"}
        </h3>
        <form onSubmit={onSubmit} className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <input value={form.owner_name} onChange={(e) => set("owner_name", e.target.value)} placeholder="Owner Name" required className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="Phone" required className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="Email" className="border rounded-lg p-2 bg-slate-50" />
          <select value={form.subscription_plan} onChange={(e) => set("subscription_plan", e.target.value)} className="border rounded-lg p-2 bg-slate-50" disabled={!!editingId}>
            {plans
              .filter((p) => p.code !== "TRIAL")
              .map((p) => (
                <option key={p.code} value={p.code}>
                  {p.name} (₹{p.price})
                </option>
              ))}
          </select>
          <div className="col-span-2 md:col-span-4 flex gap-2">
            <button type="submit" className="bg-sky-600 hover:bg-sky-700 text-white font-bold py-2 px-4 rounded-xl transition shadow">
              {editingId ? "Save Changes" : "Create Fleet"}
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
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Owner</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Phone</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Plan</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Status</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Vehicles</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody>
            {fleets.map((f) => (
              <tr key={f.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-3 text-xs font-bold text-slate-800">{f.owner_name}</td>
                <td className="p-3 text-xs text-slate-600">{f.phone}</td>
                <td className="p-3 text-xs text-slate-600">{f.plan_name || "—"}</td>
                <td className="p-3 text-xs">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${statusCls(f.subscription_status)}`}>
                    {(f.subscription_status || "TRIAL").replace("_", " ")}
                  </span>
                </td>
                <td className="p-3 text-xs text-slate-600">{f.vehicle_count} / {f.vehicle_limit}</td>
                <td className="p-3 text-xs flex gap-3">
                  <button onClick={() => startEdit(f)} className="text-sky-600 hover:text-sky-800 font-semibold">Edit</button>
                  <button onClick={() => toggle(f)} className={f.is_active ? "text-rose-600 hover:text-rose-800 font-semibold" : "text-emerald-600 hover:text-emerald-800 font-semibold"}>
                    {f.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
            {!fleets.length && (
              <tr>
                <td colSpan="6" className="p-6 text-center text-xs text-slate-400">No fleets yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}