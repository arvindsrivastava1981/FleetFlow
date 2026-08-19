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
    <div className="space-y-5">
      <div>
        <h2 className="page-title">Manage Vehicles</h2>
        <p className="page-sub">Add and maintain your fleet vehicles.</p>
      </div>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="card-pad">
        <h3 className="mb-3 text-sm font-bold text-ink-800">
          {editingId ? "Edit Vehicle" : "Add Vehicle"}
        </h3>
        <form onSubmit={onSubmit} className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3">
          <input value={form.vehicle_number} onChange={(e) => set("vehicle_number", e.target.value)} placeholder="UP32MA1234" required className="input" />
          <input value={form.make_model} onChange={(e) => set("make_model", e.target.value)} placeholder="Make / Model" className="input" />
          <input value={form.tank_capacity_liters} onChange={(e) => set("tank_capacity_liters", e.target.value)} placeholder="Tank Capacity (L)" type="number" step="any" className="input" />
          <input value={form.expected_km_per_liter} onChange={(e) => set("expected_km_per_liter", e.target.value)} placeholder="Expected km/L" type="number" step="any" className="input" />
          <input value={form.owner_phone} onChange={(e) => set("owner_phone", e.target.value)} placeholder="Owner Phone" className="input" />
          <div className="col-span-2 flex gap-2 md:col-span-3">
            <button type="submit" className="btn-primary">
              {editingId ? "Save Changes" : "Add Vehicle"}
            </button>
            {editingId && (
              <button type="button" onClick={() => { setForm(emptyForm); setEditingId(null); }} className="btn-secondary">
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Vehicle No</th>
              <th>Make / Model</th>
              <th>Fleet</th>
              <th>Tank</th>
              <th>km/L</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.map((v) => (
              <tr key={v.id}>
                <td className="font-semibold text-ink-800">{v.vehicle_number}</td>
                <td>{v.make_model || "—"}</td>
                <td>{v.fleet_owner || "—"}</td>
                <td>{v.tank_capacity_liters} L</td>
                <td>{v.expected_km_per_liter} km/L</td>
                <td>
                  <span className={`badge ${v.is_active ? "badge-success" : "badge-danger"}`}>
                    {v.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  <div className="flex gap-3 text-sm font-semibold">
                    <button onClick={() => startEdit(v)} className="text-brand-600 hover:text-brand-800">Edit</button>
                    <button onClick={() => toggle(v)} className={v.is_active ? "text-rose-600 hover:text-rose-800" : "text-emerald-600 hover:text-emerald-800"}>
                      {v.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {!vehicles.length && (
              <tr>
                <td colSpan="7" className="empty">No vehicles yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}