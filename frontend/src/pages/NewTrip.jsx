import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";
import { useToast } from "../context/ToastContext.jsx";
import { useShortcuts } from "../context/ShortcutContext.jsx";
import Loader from "../components/Loader.jsx";
import useUnsavedGuard, { LeaveGuardDialog } from "../hooks/useUnsavedGuard.jsx";

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

// Shortcuts for this page - displayed in header
const PAGE_SHORTCUTS = [
  { keys: ["1–9", "0"], label: "pick vehicle" },
  { keys: ["Shift", "1–9"], label: "pick driver" },
  { keys: ["Enter"], label: "start trip" },
];

function validate(form) {
  const errs = { ...initialErrors };
  const vehicleNo = (form.vehicle_no || "").trim().toUpperCase();
  if (vehicleNo && !PLATE_REGEX.test(vehicleNo)) {
    errs.vehicle_no = "Invalid plate — expected format like UP32MA1234";
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
  const toast = useToast();
  const { setShortcuts } = useShortcuts();
  const [form, setForm] = useState(emptyForm);
  const [vehicles, setVehicles] = useState([]);
  const [drivers, setDrivers] = useState([]);
  const [templates, setTemplates] = useState([]); // audit F-6
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [fieldErrors, setFieldErrors] = useState(initialErrors);
  const skipRef = useRef(false);
  const dirty = Boolean(
    form.vehicle_id ||
      form.driver_user_id ||
      form.vehicle_no ||
      Number(form.advance_amount || 0) !== 0 ||
      Number(form.start_odo || 0) !== 0,
  );
  const blocker = useUnsavedGuard(dirty, skipRef);

  // Set shortcuts for this page in the header
  useEffect(() => {
    setShortcuts(PAGE_SHORTCUTS);
    return () => setShortcuts([]);
  }, [setShortcuts]);

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

  // Keyboard data-entry shortcuts (no field focused):
  //  - Digit 1-9, 0  → select vehicle by position (auto-fills plate/odo/driver).
  //  - Shift+Digit    → select driver by position.
  const activeVehicles = vehicles.filter((v) => v.is_active !== false);
  const activeDrivers = drivers.filter((d) => d.is_active !== false);
  useEffect(() => {
    function onKey(e) {
      const el = e.target;
      const activeEl = document.activeElement || el;
      const isControl =
        activeEl &&
        (activeEl.tagName === "INPUT" ||
          activeEl.tagName === "SELECT" ||
          activeEl.tagName === "TEXTAREA" ||
          activeEl.tagName === "BUTTON");
      if (isControl || !/^[0-9]$/.test(e.key)) return;
      const idx = e.key === "0" ? 9 : Number(e.key) - 1;
      if (e.shiftKey) {
        const d = activeDrivers[idx];
        if (d) {
          e.preventDefault();
          set("driver_user_id", String(d.id));
        }
      } else {
        const v = activeVehicles[idx];
        if (v) {
          e.preventDefault();
          set("vehicle_id", String(v.id));
          set("vehicle_no", v.vehicle_number || "");
          if (v.last_odo != null) set("start_odo", String(v.last_odo));
          if (v.last_driver_user_id)
            set("driver_user_id", String(v.last_driver_user_id));
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [activeVehicles, activeDrivers]);

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
      const res = await api.post("/api/v1/trips", payload);
      toast.success("Trip started successfully.");
      skipRef.current = true;
      // Land on the trip detail page with expense entry
      navigate(res?.trip_code ? `/trips/${res.trip_code}/log` : "/trips");
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

  function FieldError({ msg, idFor }) {
        if (!msg) return null;
        return (
          <p id={idFor} role="alert" className="mt-1 text-[11px] text-rose-600">
            {msg}
          </p>
        );
      }

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
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <Loader label="Loading vehicles & drivers…" />
      ) : (
      <div className="card-pad">
        <form onSubmit={onSubmit} className="space-y-5 text-sm">
          {/* Phase-1 tap-first dispatch: vehicle chips (plate auto-filled). */}
          <div>
            <p className="label">
              Vehicle<Required />
            </p>
            {activeVehicles.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {activeVehicles.map((v) => (
                  <button
                    key={v.id}
                    type="button"
                    aria-pressed={String(form.vehicle_id) === String(v.id)}
                    onClick={() => {
                      set("vehicle_id", String(v.id));
                      set("vehicle_no", v.vehicle_number || "");
                      // Phase-1 prefill: last odometer + last driver chip.
                      if (v.last_odo != null) set("start_odo", String(v.last_odo));
                      if (v.last_driver_user_id) set("driver_user_id", String(v.last_driver_user_id));
                    }}
                    className={`rounded-2xl border px-4 py-3 text-left transition-all duration-200 ${
                      String(form.vehicle_id) === String(v.id)
                        ? "border-brand-500 bg-brand-50 shadow-sm ring-1 ring-brand-200"
                        : "border-ink-200 bg-white hover:bg-ink-50"
                    }`}
                  >
                    <span className="block text-base font-extrabold tracking-tight text-ink-900">
                      🚛 {v.vehicle_number}
                    </span>
                    {v.make_model && (
                      <span className="block text-[11px] text-ink-400">{v.make_model}</span>
                    )}
                  </button>
                ))}
              </div>
            ) : (
              <div>
                <input
                  id="vehicle_no"
                  value={form.vehicle_no}
                  onChange={(e) => set("vehicle_no", e.target.value.toUpperCase())}
                  placeholder="UP32MA1234"
                  required
                  autoCapitalize="characters"
                  aria-invalid={!!fieldErrors.vehicle_no}
                  aria-describedby={fieldErrors.vehicle_no ? "vehicle_no-err" : undefined}
                  className={fieldClass(!!fieldErrors.vehicle_no)}
                />
                <FieldError msg={fieldErrors.vehicle_no} idFor="vehicle_no-err" />
              </div>
            )}
          </div>

          {/* Driver chips — same tap-first pattern. */}
          <div>
            <p className="label">
              Driver<Required />
            </p>
            {activeDrivers.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {activeDrivers.map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    aria-pressed={String(form.driver_user_id) === String(d.id)}
                    onClick={() => set("driver_user_id", String(d.id))}
                    className={`rounded-2xl border px-4 py-3 text-left transition-all duration-200 ${
                      String(form.driver_user_id) === String(d.id)
                        ? "border-brand-500 bg-brand-50 shadow-sm ring-1 ring-brand-200"
                        : "border-ink-200 bg-white hover:bg-ink-50"
                    }`}
                  >
                    <span className="block text-sm font-extrabold text-ink-900">
                      👨 {d.full_name}
                    </span>
                    {d.phone && (
                      <span className="block text-[11px] text-ink-400">{d.phone}</span>
                    )}
                  </button>
                ))}
              </div>
            ) : (
              <select
                id="driver_user_id"
                value={form.driver_user_id}
                onChange={(e) => set("driver_user_id", e.target.value)}
                className="input"
                required
              >
                <option value="">Select Driver</option>
                {drivers.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.full_name}
                    {d.phone ? ` (${d.phone})` : ""}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* ₹0 advance allowed — many trips start with no cash given. */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="advance_amount">
                Advance Amount (₹)
              </label>
              <input
                id="advance_amount"
                value={form.advance_amount}
                onChange={(e) => set("advance_amount", e.target.value)}
                placeholder="0.00"
                type="number"
                inputMode="decimal"
                step="any"
                min="0"
                aria-invalid={!!fieldErrors.advance_amount}
                aria-describedby={fieldErrors.advance_amount ? "advance_amount-err" : undefined}
                className={fieldClass(!!fieldErrors.advance_amount)}
              />
              <FieldError msg={fieldErrors.advance_amount} idFor="advance_amount-err" />
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
                inputMode="decimal"
                step="any"
                min="0"
                required
                aria-invalid={!!fieldErrors.start_odo}
                aria-describedby={fieldErrors.start_odo ? "start_odo-err" : undefined}
                className={fieldClass(!!fieldErrors.start_odo)}
              />
              <FieldError msg={fieldErrors.start_odo} idFor="start_odo-err" />
            </div>
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="btn-primary flex-1 py-3 text-base"
            >
              {busy ? "Creating…" : "🚚 Start Trip"}
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
      <LeaveGuardDialog blocker={blocker} onLeave={() => blocker.proceed()} />
    </div>
  );
}