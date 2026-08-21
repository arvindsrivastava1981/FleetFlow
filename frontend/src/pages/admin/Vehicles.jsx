import { useEffect, useState } from "react";
import { api } from "../../lib/api.js";
import { useToast } from "../../context/ToastContext.jsx";
import Loader from "../../components/Loader.jsx";

// Standard Indian registration plate regex (system invariant).
const PLATE_REGEX = /^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$/;

const emptyForm = {
  vehicle_number: "",
  make_model: "",
  tank_capacity_liters: "",
  expected_km_per_liter: "",
  owner_phone: "",
};

const initialErrors = {
  vehicle_number: "",
  make_model: "",
  tank_capacity_liters: "",
  expected_km_per_liter: "",
};

function Required() {
  return <span className="text-rose-500 ml-0.5">*</span>;
}

function FieldError({ msg }) {
  if (!msg) return null;
  return <p className="mt-1 text-[11px] text-rose-600">{msg}</p>;
}

function validate(form) {
  const errs = { ...initialErrors };
  const plate = (form.vehicle_number || "").trim().toUpperCase();
  if (!plate) {
    errs.vehicle_number = "Vehicle number is required.";
  } else if (!PLATE_REGEX.test(plate)) {
    errs.vehicle_number = "Invalid plate — expected format like UP32MA1234.";
  }
  if (!form.make_model.trim()) {
    errs.make_model = "Make / Model is required.";
  }
  const tank = Number(form.tank_capacity_liters);
  if (form.tank_capacity_liters === "" || Number.isNaN(tank)) {
    errs.tank_capacity_liters = "Tank capacity is required.";
  } else if (tank <= 0) {
    errs.tank_capacity_liters = "Tank capacity must be greater than 0.";
  }
  const kmpl = Number(form.expected_km_per_liter);
  if (form.expected_km_per_liter !== "" && !Number.isNaN(kmpl) && kmpl <= 0) {
    errs.expected_km_per_liter = "Expected km/L must be greater than 0.";
  }
  return errs;
}

export default function VehiclesPage() {
  const toast = useToast();
  const [vehicles, setVehicles] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [fieldErrors, setFieldErrors] = useState(initialErrors);
  const [busy, setBusy] = useState(false);

  function load() {
    api
      .get("/api/v1/vehicles")
      .then(setVehicles)
      .catch((e) => {
        setError(e.message);
        toast.error(e.message);
      })
      .finally(() => setLoading(false));
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
      setError("Please fix the highlighted fields before saving.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const payload = {
        vehicle_number: form.vehicle_number.trim().toUpperCase(),
        make_model: form.make_model.trim(),
        tank_capacity_liters:
          form.tank_capacity_liters !== ""
            ? Number(form.tank_capacity_liters)
            : 350,
        expected_km_per_liter:
          form.expected_km_per_liter !== ""
            ? Number(form.expected_km_per_liter)
            : 4,
        owner_phone: form.owner_phone.trim() || null,
      };
      if (editingId) {
        await api.put(`/api/v1/vehicles/${editingId}`, payload);
        toast.success("Vehicle updated.");
      } else {
        await api.post("/api/v1/vehicles", payload);
        toast.success("Vehicle added.");
      }
      setForm(emptyForm);
      setEditingId(null);
      setFieldErrors(initialErrors);
      load();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  function startEdit(v) {
    setEditingId(v.id);
    setForm({
      vehicle_number: v.vehicle_number,
      make_model: v.make_model || "",
      tank_capacity_liters: String(v.tank_capacity_liters ?? ""),
      expected_km_per_liter: String(v.expected_km_per_liter ?? ""),
      owner_phone: v.owner_phone || "",
    });
    setFieldErrors(initialErrors);
    setError("");
  }

  async function toggle(v) {
    try {
      await api.post(`/api/v1/vehicles/${v.id}/toggle`, { activate: !v.is_active });
      toast.success(v.is_active ? "Vehicle deactivated." : "Vehicle activated.");
      load();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    }
  }

  function fieldClass(hasError) {
    return `input ${hasError ? "input-error" : ""}`;
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="page-title">Manage Vehicles</h2>
        <p className="page-sub">Add and maintain your fleet vehicles.</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card-pad">
        <h3 className="mb-4 text-sm font-bold text-ink-800">
          {editingId ? "Edit Vehicle" : "Add Vehicle"}
        </h3>
        <form
          onSubmit={onSubmit}
          className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3"
        >
          {/* Vehicle Number */}
          <div>
            <label className="label" htmlFor="vehicle_number">
              Vehicle Number <Required />
            </label>
            <input
              id="vehicle_number"
              value={form.vehicle_number}
              onChange={(e) => set("vehicle_number", e.target.value)}
              placeholder="e.g. TS07GK4191"
              required
              className={fieldClass(!!fieldErrors.vehicle_number)}
            />
            <FieldError msg={fieldErrors.vehicle_number} />
          </div>

          {/* Make / Model */}
          <div>
            <label className="label" htmlFor="make_model">
              Make / Model <Required />
            </label>
            <input
              id="make_model"
              value={form.make_model}
              onChange={(e) => set("make_model", e.target.value)}
              placeholder="e.g. TATA / 2019"
              required
              className={fieldClass(!!fieldErrors.make_model)}
            />
            <FieldError msg={fieldErrors.make_model} />
          </div>

          {/* Tank Capacity */}
          <div>
            <label className="label" htmlFor="tank_capacity_liters">
              Tank Capacity (L) <Required />
            </label>
            <input
              id="tank_capacity_liters"
              value={form.tank_capacity_liters}
              onChange={(e) => set("tank_capacity_liters", e.target.value)}
              placeholder="e.g. 350"
              type="number"
              step="any"
              min="0.1"
              required
              className={fieldClass(!!fieldErrors.tank_capacity_liters)}
            />
            <FieldError msg={fieldErrors.tank_capacity_liters} />
          </div>

          {/* Expected Km/L */}
          <div>
            <label className="label" htmlFor="expected_km_per_liter">
              Expected Km/L
            </label>
            <input
              id="expected_km_per_liter"
              value={form.expected_km_per_liter}
              onChange={(e) => set("expected_km_per_liter", e.target.value)}
              placeholder="e.g. 4.0"
              type="number"
              step="any"
              min="0.1"
              className={fieldClass(!!fieldErrors.expected_km_per_liter)}
            />
            <FieldError msg={fieldErrors.expected_km_per_liter} />
          </div>

          {/* Owner Phone */}
          <div>
            <label className="label" htmlFor="owner_phone">
              Owner Phone
            </label>
            <input
              id="owner_phone"
              value={form.owner_phone}
              onChange={(e) => set("owner_phone", e.target.value)}
              placeholder="e.g. 08860666659"
              className="input"
            />
          </div>

          {/* Actions */}
          <div className="sm:col-span-2 lg:col-span-3 flex gap-2">
            <button type="submit" disabled={busy} className="btn-primary">
              {busy ? "Saving…" : editingId ? "Save Changes" : "Add Vehicle"}
            </button>
            {editingId && (
              <button
                type="button"
                onClick={() => { setForm(emptyForm); setEditingId(null); setFieldErrors(initialErrors); setError(""); }}
                className="btn-secondary"
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      {loading ? (
        <Loader label="Loading vehicles…" />
      ) : (
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
      )}
    </div>
  );
}