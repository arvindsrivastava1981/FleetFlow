import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";

// Standard Indian registration plate regex (system invariant).
const PLATE_REGEX = /^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$/;

const emptyForm = {
  vehicle_no: "",
  driver_name: "",
  driver_phone: "",
  advance_amount: "0",
  start_odo: "0",
  vehicle_id: "",
  driver_user_id: "",
};

const initialErrors = {
  vehicle_no: "",
  driver_phone: "",
  advance_amount: "",
  start_odo: "",
};

function validate(form) {
  const errs = { ...initialErrors };
  const vehicleNo = (form.vehicle_no || "").trim().toUpperCase();
  if (vehicleNo && !PLATE_REGEX.test(vehicleNo)) {
    errs.vehicle_no = "Invalid plate — expected format like UP32MA1234";
  }
  const phone = (form.driver_phone || "").trim();
  if (phone && !/^\+91[6-9][0-9]{9}$/.test(phone)) {
    errs.driver_phone = "Phone must match +91 6-9 9-digit (e.g. +919876543210)";
  }
  const advance = Number(form.advance_amount || 0);
  if (Number.isNaN(advance)) {
    errs.advance_amount = "Advance must be a number";
  } else if (advance < 0) {
    errs.advance_amount = "Advance cannot be negative";
  }
  const odo = Number(form.start_odo || 0);
  if (Number.isNaN(odo)) {
    errs.start_odo = "Odometer must be a number";
  } else if (odo < 0) {
    errs.start_odo = "Odometer cannot be negative";
  }
  return errs;
}

export default function NewTripPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(emptyForm);
  const [vehicles, setVehicles] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [fieldErrors, setFieldErrors] = useState(initialErrors);

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
    setFieldErrors((e) => ({ ...e, [k]: "" }));
  }

  async function onSubmit(e) {
    e.preventDefault();
    const errs = validate(form);
    setFieldErrors(errs);
    if (Object.values(errs).some(Boolean)) {
      setError("Please fix the highlighted fields before starting the trip.");
      return;
    }
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

  function fieldClass(hasError) {
    return `border rounded-lg p-2 bg-slate-50 ${
      hasError ? "border-rose-400" : ""
    }`;
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
            className={fieldClass(!!fieldErrors.vehicle_no)}
          />
          {fieldErrors.vehicle_no && (
            <p className="col-span-2 md:col-span-3 text-[11px] text-rose-600">
              {fieldErrors.vehicle_no}
            </p>
          )}
          <input
            value={form.driver_name}
            onChange={(e) => set("driver_name", e.target.value)}
            placeholder="Driver Name"
            required
            disabled={!!form.driver_user_id}
            className={fieldClass(false)}
          />
          <input
            value={form.driver_phone}
            onChange={(e) => set("driver_phone", e.target.value)}
            placeholder="Driver Phone (+91...)"
            required
            className={fieldClass(!!fieldErrors.driver_phone)}
          />
          {fieldErrors.driver_phone && (
            <p className="col-span-2 md:col-span-3 text-[11px] text-rose-600">
              {fieldErrors.driver_phone}
            </p>
          )}
          <input
            value={form.advance_amount}
            onChange={(e) => set("advance_amount", e.target.value)}
            placeholder="Advance Amount ₹"
            type="number"
            step="any"
            min="0"
            required
            className={fieldClass(!!fieldErrors.advance_amount)}
          />
          {fieldErrors.advance_amount && (
            <p className="col-span-2 md:col-span-3 text-[11px] text-rose-600">
              {fieldErrors.advance_amount}
            </p>
          )}
          <input
            value={form.start_odo}
            onChange={(e) => set("start_odo", e.target.value)}
            placeholder="Start Odometer (KM)"
            type="number"
            step="any"
            min="0"
            required
            className={fieldClass(!!fieldErrors.start_odo)}
          />
          {fieldErrors.start_odo && (
            <p className="col-span-2 md:col-span-3 text-[11px] text-rose-600">
              {fieldErrors.start_odo}
            </p>
          )}

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