import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";

const emptyForm = {
  vehicle_no: "",
  driver_name: "",
  driver_phone: "",
  advance_amount: "0",
  start_odo: "0",
  vehicle_id: "",
  driver_user_id: "",
};

export default function NewTripPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyForm);
  const [vehicles, setVehicles] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    api
      .get("/api/v1/vehicles")
      .then(setVehicles)
      .catch((e) => setError(e.message));
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
    setBusy(true);
    setError("");
    try {
      const payload = {
        vehicle_no: String(form.vehicle_id)
          ? vehicles.find((v) => String(v.id) === String(form.vehicle_id))
            ?.vehicle_number || form.vehicle_no
          : form.vehicle_no,
        driver_name: form.driver_name,
        driver_phone: form.driver_phone,
        advance_amount: Number(form.advance_amount || 0),
        start_odo: Number(form.start_odo || 0),
        vehicle_id: form.vehicle_id ? Number(form.vehicle_id) : null,
        driver_user_id: form.driver_user_id
          ? Number(form.driver_user_id)
          : null,
      };
      await api.post("/api/v1/trips", payload);
      navigate("/trips");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const activeVehicles = vehicles.filter((v) => v.is_active !== false);
  const activeDrivers = drivers.filter((d) => d.is_active !== false);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-between items-center gap-2">
        <h2 className="text-lg font-extrabold text-slate-900">Start New Trip</h2>
      </div>
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <form onSubmit={onSubmit} className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <select
            value={form.vehicle_id}
            onChange={(e) => {
              const vid = e.target.value;
              const v = vehicles.find((x) => String(x.id) === String(vid));
              set("vehicle_id", vid);
              set("vehicle_no", v?.vehicle_number || "");
            }}
            className="border rounded-lg p-2 bg-slate-50"
            required
          >
            <option value="">Select Vehicle</option>
            {activeVehicles.map((v) => (
              <option key={v.id} value={v.id}>
                {v.vehicle_number}
              </option>
            ))}
          </select>

          <select
            value={form.driver_user_id}
            onChange={(e) => {
              const uid = e.target.value;
              const d = drivers.find((x) => String(x.id) === String(uid));
              set("driver_user_id", uid);
              set("driver_name", d?.full_name || "");
            }}
            className="border rounded-lg p-2 bg-slate-50"
          >
            <option value="">Select Driver</option>
            {activeDrivers.map((d) => (
              <option key={d.id} value={d.id}>
                {d.full_name}
              </option>
            ))}
          </select>

          <input
            value={form.vehicle_no}
            onChange={(e) => set("vehicle_no", e.target.value)}
            placeholder="Vehicle No (UP32MA1234)"
            required
            disabled={!!form.vehicle_id}
            className="border rounded-lg p-2 bg-slate-50 disabled:opacity-50"
          />
          <input
            value={form.driver_name}
            onChange={(e) => set("driver_name", e.target.value)}
            placeholder="Driver Name"
            required
            disabled={!!form.driver_user_id}
            className="border rounded-lg p-2 bg-slate-50 disabled:opacity-50"
          />
          <input
            value={form.driver_phone}
            onChange={(e) => set("driver_phone", e.target.value)}
            placeholder="Driver Phone (+91...)"
            required
            className="border rounded-lg p-2 bg-slate-50"
          />
          <input
            value={form.advance_amount}
            onChange={(e) => set("advance_amount", e.target.value)}
            placeholder="Advance Amount ₹"
            type="number"
            step="any"
            min="0"
            required
            className="border rounded-lg p-2 bg-slate-50"
          />
          <input
            value={form.start_odo}
            onChange={(e) => set("start_odo", e.target.value)}
            placeholder="Start Odometer (KM)"
            type="number"
            step="any"
            min="0"
            required
            className="border rounded-lg p-2 bg-slate-50"
          />

          <div className="col-span-2 md:col-span-3 flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="bg-sky-600 hover:bg-sky-700 text-white font-bold py-2 px-4 rounded-xl transition shadow disabled:opacity-50"
            >
              {busy ? "Creating…" : "Start Trip"}
            </button>
            <button
              type="button"
              onClick={() => navigate("/trips")}
              className="bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-2 px-4 rounded-xl"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}