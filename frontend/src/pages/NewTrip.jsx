import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";
import { useToast } from "../context/ToastContext.jsx";
import Loader from "../components/Loader.jsx";

// Standard Indian registration plate regex (system invariant).
const PLATE_REGEX = /^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$/;

const emptyForm = {
  vehicle_no: "",
  advance_amount: "0",
  start_odo: "0",
  vehicle_id: "",
  driver_user_id: "",
};

const initialErrors = {
  vehicle_no: "",
  advance_amount: "",
  start_odo: "",
};

function validate(form) {
  const errs = { ...initialErrors };
  const vehicleNo = (form.vehicle_no || "").trim().toUpperCase();
  if (vehicleNo && !PLATE_REGEX.test(vehicleNo)) {
    errs.vehicle_no = "Invalid plate — expected format like UP32MA1234";
  }
  const advance = Number(form.advance_amount || 0);
  if (Number.isNaN(advance)) {
    errs.advance_amount = "Advance must be a number";
  } else if (advance <= 0) {
    errs.advance_amount = "Advance must be greater than zero";
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
  const toast = useToast();
  const [form, setForm] = useState(emptyForm);
  const [vehicles, setVehicles] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [templates, setTemplates] = useState([]); // audit F-6
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [fieldErrors, setFieldErrors] = useState(initialErrors);

  function load() {
    api
      .get("/api/v1/vehicles")
      .then(setVehicles)
      .catch((e) => setError(e.message));
    api
      .get("/api/v1/drivers")
      .then(setDrivers)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    // Audit F-6: reusable route templates for one-tap prefill.
    api
      .get("/api/v1/trip-templates")
      .then(setTemplates)
      .catch(() => {}); // templates are optional polish — never block dispatch
  }
  useEffect(load, []);

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
    setFieldErrors((e) => ({ ...e, [k]: "" }));
  }

  // Audit F-6: fill vehicle/driver from a saved route template.
  function applyTemplate(id) {
    const t = templates.find((x) => String(x.id) === String(id));
    if (!t) return;
    setForm((f) => ({
      ...f,
      vehicle_id: t.vehicle_id ? String(t.vehicle_id) : f.vehicle_id,
      driver_user_id: t.driver_user_id
        ? String(t.driver_user_id)
        : f.driver_user_id,
      vehicle_no: t.vehicle_id
        ? vehicles.find((v) => String(v.id) === String(t.vehicle_id))
            ?.vehicle_number || f.vehicle_no
        : f.vehicle_no,
    }));
    toast.success(`Template "${t.name}" loaded — review & start the trip.`);
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
        advance_amount: Number(form.advance_amount || 0),
        start_odo: Number(form.start_odo || 0),
        vehicle_id: form.vehicle_id ? Number(form.vehicle_id) : null,
        driver_user_id: form.driver_user_id
          ? Number(form.driver_user_id)
          : null,
      };
      await api.post("/api/v1/trips", payload);
      toast.success("Trip started successfully.");
      navigate("/trips");
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  function fieldClass(hasError) {
    return `input ${hasError ? "input-error" : ""}`;
  }

  function Required() {
    return <span className="text-rose-500"> *</span>;
  }

  function FieldError({ msg }) {
    if (!msg) return null;
    return <p className="mt-1 text-[11px] text-rose-600">{msg}</p>;
  }

  const activeVehicles = vehicles.filter((v) => v.is_active !== false);
  const activeDrivers = drivers.filter((d) => d.is_active !== false);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-between items-center gap-2">
        <div>
          <h2 className="page-title">Start New Trip</h2>
          <p className="page-sub">Dispatch a vehicle with an assigned driver.</p>
        </div>
      </div>

      {templates.length > 0 && (
        <div className="card-pad flex flex-wrap items-center gap-3">
          <span className="text-xs font-bold uppercase tracking-wider text-ink-500">
            📋 Start from template
          </span>
          <select
            className="input max-w-[280px]"
            value=""
            onChange={(e) => applyTemplate(e.target.value)}
          >
            <option value="">Choose a saved route…</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
                {t.vehicle_number ? ` · ${t.vehicle_number}` : ""}
                {t.driver_name ? ` · ${t.driver_name}` : ""}
              </option>
            ))}
          </select>
        </div>
      )}

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {loading ? (
        <Loader label="Loading vehicles & drivers…" />
      ) : (
      <div className="card-pad">
        <form onSubmit={onSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 text-sm">
          <div>
            <label className="label" htmlFor="vehicle_id">
              Vehicle<Required />
            </label>
            <select
              id="vehicle_id"
              value={form.vehicle_id}
              onChange={(e) => {
                const vid = e.target.value;
                const v = vehicles.find((x) => String(x.id) === String(vid));
                set("vehicle_id", vid);
                set("vehicle_no", v?.vehicle_number || "");
              }}
              className="input"
              required
            >
              <option value="">Select Vehicle</option>
              {activeVehicles.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.vehicle_number} {v.make_model ? ` · ${v.make_model}` : ""}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="driver_user_id">
              Driver<Required />
            </label>
            <select
              id="driver_user_id"
              value={form.driver_user_id}
              onChange={(e) => {
                const uid = e.target.value;
                set("driver_user_id", uid);
              }}
              className="input"
              required
            >
              <option value="">Select Driver</option>
              {activeDrivers.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.full_name}
                  {d.phone ? ` (${d.phone})` : ""}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="vehicle_no">
              Vehicle No<Required />
            </label>
            <input
              id="vehicle_no"
              value={form.vehicle_no}
              onChange={(e) => set("vehicle_no", e.target.value)}
              placeholder="UP32MA1234"
              required
              disabled={!!form.vehicle_id}
              className={fieldClass(!!fieldErrors.vehicle_no)}
            />
            <FieldError msg={fieldErrors.vehicle_no} />
          </div>

          <div>
            <label className="label" htmlFor="advance_amount">
              Advance Amount (₹)<Required />
            </label>
            <input
              id="advance_amount"
              value={form.advance_amount}
              onChange={(e) => set("advance_amount", e.target.value)}
              placeholder="0.00"
              type="number"
              step="any"
              min="0.01"
              required
              className={fieldClass(!!fieldErrors.advance_amount)}
            />
            <FieldError msg={fieldErrors.advance_amount} />
          </div>

          <div>
            <label className="label" htmlFor="start_odo">
              Start Odometer (KM)<Required />
            </label>
            <input
              id="start_odo"
              value={form.start_odo}
              onChange={(e) => set("start_odo", e.target.value)}
              placeholder="0"
              type="number"
              step="any"
              min="0"
              required
              className={fieldClass(!!fieldErrors.start_odo)}
            />
            <FieldError msg={fieldErrors.start_odo} />
          </div>

          <div className="md:col-span-2 lg:col-span-3 flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="btn-primary"
            >
              {busy ? "Creating…" : "Start Trip"}
            </button>
            <button
              type="button"
              onClick={() => navigate("/trips")}
              className="btn-secondary"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
      )}
    </div>
  );
}