import { useEffect, useState } from "react";
import { api } from "../../lib/api.js";

const emptyForm = {
  vehicle_number: "",
  make_model: "",
  tank_capacity_liters: "350",
  expected_km_per_liter: "4",
  owner_phone: "",
};

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);

  function load() {
    api
      .get("/api/v1/vehicles")
      .then(setVehicles)
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
      const payload = {
        ...form,
        tank_capacity_liters: Number(form.tank_capacity_liters),
        expected_km_per_liter: Number(form.expected_km_per_liter),
      };
      if (editingId) {
        await api.put(`/api/v1/vehicles/${editingId}`, payload);
      } else {
        await api.post("/api/v1/vehicles", payload);
      }
      setForm(emptyForm);
      setEditingId(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  function startEdit(v) {
    setEditingId(v.id);
    setForm({
      vehicle_number: v.vehicle_number,
      make_model: v.make_model || "",
      tank_capacity_liters: String(v.tank_capacity_liters),
      expected_km_per_liter: String(v.expected_km_per_liter),
      owner_phone: v.owner_phone || "",
    });
  }

  async function toggle(v) {
    try {
      await api.post(`/api/v1/vehicles/${v.id}/toggle`, { activate: !v.is_active });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-extrabold text-slate-900">Manage Vehicles</h2>
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <h3 className="text-sm font-extrabold text-slate-800 mb-3">
          {editingId ? "Edit Vehicle" : "Add Vehicle"}
        </h3>
        <form onSubmit={onSubmit} className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <input value={form.vehicle_number} onChange={(e) => set("vehicle_number", e.target.value)} placeholder="UP32MA1234" required className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.make_model} onChange={(e) => set("make_model", e.target.value)} placeholder="Make / Model" className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.tank_capacity_liters} onChange={(e) => set("tank_capacity_liters", e.target.value)} placeholder="Tank Capacity (L)" type="number" step="any" className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.expected_km_per_liter} onChange={(e) => set("expected_km_per_liter", e.target.value)} placeholder="Expected km/L" type="number" step="any" className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.owner_phone} onChange={(e) => set("owner_phone", e.target.value)} placeholder="Owner Phone" className="border rounded-lg p-2 bg-slate-50" />
          <div className="col-span-2 md:col-span-3 flex gap-2">
            <button type="submit" className="bg-sky-600 hover:bg-sky-700 text-white font-bold py-2 px-4 rounded-xl transition shadow">
              {editingId ? "Save Changes" : "Add Vehicle"}
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
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Vehicle No</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Make / Model</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Fleet</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Tank</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">km/L</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Status</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.map((v) => (
              <tr key={v.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-3 text-xs font-bold text-slate-800">{v.vehicle_number}</td>
                <td className="p-3 text-xs text-slate-600">{v.make_model || "—"}</td>
                <td className="p-3 text-xs text-slate-600">{v.fleet_owner || "—"}</td>
                <td className="p-3 text-xs text-slate-600">{v.tank_capacity_liters} L</td>
                <td className="p-3 text-xs text-slate-600">{v.expected_km_per_liter} km/L</td>
                <td className="p-3 text-xs">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${v.is_active ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
                    {v.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="p-3 text-xs flex gap-3">
                  <button onClick={() => startEdit(v)} className="text-sky-600 hover:text-sky-800 font-semibold">Edit</button>
                  <button onClick={() => toggle(v)} className={v.is_active ? "text-rose-600 hover:text-rose-800 font-semibold" : "text-emerald-600 hover:text-emerald-800 font-semibold"}>
                    {v.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
            {!vehicles.length && (
              <tr>
                <td colSpan="7" className="p-6 text-center text-xs text-slate-400">No vehicles yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}