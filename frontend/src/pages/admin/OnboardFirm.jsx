import { useState } from "react";
import { api } from "../../lib/api.js";
import { useToast } from "../../context/ToastContext.jsx";

const PLANS = [
  { code: "TRIAL", name: "Trial Pack", desc: "15 days free · 1 vehicle" },
  { code: "MONTHLY", name: "Monthly", desc: "₹799 · 1 vehicle · month" },
  { code: "YEARLY", name: "Yearly", desc: "₹7,191 · 1 vehicle · year (25% off)" },
];

const BATTA_TYPES = ["FIXED_TRIP", "PER_KM", "DAILY", "NONE"];
const PLATE_RE = /^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$/;
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export default function OnboardFirmPage() {
  const toast = useToast();
  const [form, setForm] = useState({
    owner_name: "", phone: "", owner_email: "",
    email: "", full_name: "", password: "",
    plan_code: "TRIAL",
    vehicle_number: "", make_model: "", tank_capacity_liters: "", expected_km_per_liter: "",
    driver_email: "", driver_full_name: "", driver_password: "", driver_phone: "",
    batta_type: "FIXED_TRIP", batta_rate: "",
  });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const input = "input";

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
    setErrors((e) => ({ ...e, [k]: undefined }));
  }

  function validate() {
    const e = {};
    if (!form.owner_name.trim()) e.owner_name = "Firm / owner name is required.";
    if (!form.phone.trim()) e.phone = "Phone is required.";
    if (!form.email.trim()) e.email = "Manager email is required.";
    else if (!EMAIL_RE.test(form.email.trim())) e.email = "Enter a valid email address.";
    if (!form.full_name.trim()) e.full_name = "Manager full name is required.";
    if (!form.password.trim()) e.password = "Manager password is required.";
    else if (form.password.length < 8) e.password = "Password must be at least 8 characters.";

    if (form.vehicle_number) {
      const plate = form.vehicle_number.trim().toUpperCase();
      if (!PLATE_RE.test(plate)) e.vehicle_number = "Enter a valid plate, e.g. UP32TA1234.";
      if (form.tank_capacity_liters != null &&
          form.tank_capacity_liters !== "" &&
          Number(form.tank_capacity_liters) <= 0) {
        e.tank_capacity_liters = "Tank capacity must be greater than 0.";
      }
      if (form.expected_km_per_liter != null &&
          form.expected_km_per_liter !== "" &&
          Number(form.expected_km_per_liter) <= 0) {
        e.expected_km_per_liter = "Expected km/L must be greater than 0.";
      }
    }

    if (form.driver_email && form.driver_full_name && form.driver_password) {
      if (!form.driver_email.trim()) e.driver_email = "Driver email is required.";
      else if (!EMAIL_RE.test(form.driver_email.trim())) e.driver_email = "Enter a valid email address.";
      if (!form.driver_full_name.trim()) e.driver_full_name = "Driver full name is required.";
      if (form.driver_password.length < 8) e.driver_password = "Driver password must be at least 8 characters.";
    } else if (form.driver_email || form.driver_full_name || form.driver_password || form.driver_phone) {
      e.driver_group = "Fill all driver fields (email, name and password) to add the driver.";
    }

    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    if (!validate()) return;
    setSubmitting(true);
    const payload = {
      fleet: { owner_name: form.owner_name, phone: form.phone, email: form.email || null },
      owner: { email: form.owner_email || form.email, full_name: form.full_name, password: form.password, is_trip_manager: true },
      plan_code: form.plan_code,
    };
    if (form.vehicle_number) {
      payload.initial_vehicle = {
        vehicle_number: form.vehicle_number,
        make_model: form.make_model || null,
        tank_capacity_liters: form.tank_capacity_liters ? Number(form.tank_capacity_liters) : 350.0,
        expected_km_per_liter: form.expected_km_per_liter ? Number(form.expected_km_per_liter) : 4.0,
      };
    }
    if (form.driver_email && form.driver_full_name && form.driver_password) {
      payload.initial_driver = {
        email: form.driver_email, full_name: form.driver_full_name,
        password: form.driver_password, phone: form.driver_phone || null,
        batta_type: form.batta_type,
        default_batta_rate: form.batta_rate ? Number(form.batta_rate) : null,
      };
    }
    try {
      const data = await api.post("/api/v1/fleets/onboard", payload);
      setResult(data);
      setErrors({});
      toast.success("Firm onboarded successfully.");
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="page-title">Onboard a Transport Firm</h2>
      <p className="text-xs text-slate-500">Create a whole firm — fleet + owner Trip Manager + subscription — in one step (Super Admin).</p>
      {error && <div className="alert alert-error">{error}</div>}
      {result && (
        <div className="alert alert-success space-y-1">
          <p className="font-bold">Firm created</p>
          <p>Fleet ID: {result.fleet_id} · Owner user ID: {result.owner_user_id}</p>
          <p>Vehicle ID: {result.vehicle_id || "—"} · Driver ID: {result.driver_user_id || "—"}</p>
          <p>Plan: {result.plan_code}</p>
          <p>{result.email_queued ? "✓ Welcome email queued to the manager." : "Note: manager onboarding email not sent (no manager email)."}</p>
          {result.payment_url && (
            <p>Payment link: <a className="underline text-emerald-700" href={result.payment_url} target="_blank" rel="noreferrer">open checkout</a></p>
          )}
          <button
            type="button"
            onClick={() => { setResult(null); setError(""); setErrors({}); setForm({ owner_name: "", phone: "", owner_email: "", email: "", full_name: "", password: "", plan_code: "TRIAL", vehicle_number: "", make_model: "", tank_capacity_liters: "", expected_km_per_liter: "", driver_email: "", driver_full_name: "", driver_password: "", driver_phone: "", batta_type: "FIXED_TRIP", batta_rate: "" }); }}
            className="btn-secondary mt-2"
          >
            Onboard another firm
          </button>
        </div>
      )}

      <form onSubmit={onSubmit} className="card-pad space-y-5" noValidate>
        <div>
          <h3 className="mb-3 text-sm font-extrabold text-slate-800">1. Firm details</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <label className="block text-xs font-semibold text-slate-600">
              Firm / Owner Name <span className="text-rose-500">*</span>
              <input value={form.owner_name} onChange={(e) => set("owner_name", e.target.value)} placeholder="e.g. Arvind Transport" className={input} />
              {errors.owner_name && <span className="mt-1 block text-[11px] text-rose-600">{errors.owner_name}</span>}
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Phone <span className="text-rose-500">*</span>
              <input value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="e.g. +91 98765 43210" className={input} />
              {errors.phone && <span className="mt-1 block text-[11px] text-rose-600">{errors.phone}</span>}
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Email
              <input value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="owner@firm.com" type="email" className={input} />
              {errors.email && <span className="mt-1 block text-[11px] text-rose-600">{errors.email}</span>}
            </label>
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-extrabold text-slate-800">2. Owner / Trip Manager account</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <label className="block text-xs font-semibold text-slate-600">
              Manager Email <span className="text-rose-500">*</span>
              <input value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="e.g. arvind@firm.com" className={input} />
              {errors.email && <span className="mt-1 block text-[11px] text-rose-600">{errors.email}</span>}
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Full Name <span className="text-rose-500">*</span>
              <input value={form.full_name} onChange={(e) => set("full_name", e.target.value)} placeholder="e.g. Arvind Srivastava" className={input} />
              {errors.full_name && <span className="mt-1 block text-[11px] text-rose-600">{errors.full_name}</span>}
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Temporary Password <span className="text-rose-500">*</span>
              <input value={form.password} onChange={(e) => set("password", e.target.value)} placeholder="Min 8 characters" type="password" className={input} />
              {errors.password && <span className="mt-1 block text-[11px] text-rose-600">{errors.password}</span>}
            </label>
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-extrabold text-slate-800">3. Subscription plan</h3>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-3 text-sm">
            {PLANS.map((p) => (
              <label key={p.code} className={`cursor-pointer rounded-xl border p-3 ${form.plan_code === p.code ? "border-brand-500 bg-brand-50" : "border-ink-200"}`}>
                <input type="radio" name="plan_code" value={p.code} checked={form.plan_code === p.code} onChange={(e) => set("plan_code", e.target.value)} className="mr-2" />
                <span className="font-bold">{p.name}</span>
                <span className="block text-[10px] text-slate-500">{p.desc}</span>
              </label>
            ))}
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-extrabold text-slate-800">4. Optional first vehicle</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <label className="block text-xs font-semibold text-slate-600">
              Vehicle Number
              <input value={form.vehicle_number} onChange={(e) => set("vehicle_number", e.target.value.toUpperCase())} placeholder="e.g. UP32TA1234" className={input} />
              {errors.vehicle_number && <span className="mt-1 block text-[11px] text-rose-600">{errors.vehicle_number}</span>}
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Make / Model
              <input value={form.make_model} onChange={(e) => set("make_model", e.target.value)} placeholder="e.g. Tata 407" className={input} />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Tank Capacity (L)
              <input value={form.tank_capacity_liters} onChange={(e) => set("tank_capacity_liters", e.target.value)} placeholder="e.g. 350" type="number" min="1" className={input} />
              {errors.tank_capacity_liters && <span className="mt-1 block text-[11px] text-rose-600">{errors.tank_capacity_liters}</span>}
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Expected Km/L
              <input value={form.expected_km_per_liter} onChange={(e) => set("expected_km_per_liter", e.target.value)} placeholder="e.g. 4.0" type="number" min="0.1" step="any" className={input} />
              {errors.expected_km_per_liter && <span className="mt-1 block text-[11px] text-rose-600">{errors.expected_km_per_liter}</span>}
            </label>
          </div>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-extrabold text-slate-800">5. Optional first driver</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <label className="block text-xs font-semibold text-slate-600">
              Driver Email
              <input value={form.driver_email} onChange={(e) => set("driver_email", e.target.value)} placeholder="e.g. raju@firm.com" className={input} />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Driver Full Name
              <input value={form.driver_full_name} onChange={(e) => set("driver_full_name", e.target.value)} placeholder="e.g. Raju Kumar" className={input} />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Driver Password
              <input value={form.driver_password} onChange={(e) => set("driver_password", e.target.value)} placeholder="Min 8 characters" type="password" className={input} />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Driver Phone
              <input value={form.driver_phone} onChange={(e) => set("driver_phone", e.target.value)} placeholder="+91 91234 56789" className={input} />
            </label>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="block text-xs font-semibold text-slate-600">
              Driver Salary / Bhatta Type
              <select value={form.batta_type} onChange={(e) => set("batta_type", e.target.value)} className={input}>
                {BATTA_TYPES.map((bt) => (
                  <option key={bt} value={bt}>{bt.replace(/_/g, " ")}</option>
                ))}
              </select>
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Batta Rate
              <input value={form.batta_rate} onChange={(e) => set("batta_rate", e.target.value)} placeholder="e.g. 2500" type="number" disabled={form.batta_type === "NONE"} className={`${input} disabled:opacity-50`} />
            </label>
          </div>
          {errors.driver_group && <p className="mt-2 text-[11px] text-rose-600">{errors.driver_group}</p>}
          {errors.driver_email && <p className="mt-1 text-[11px] text-rose-600">{errors.driver_email}</p>}
          {errors.driver_full_name && <p className="mt-1 text-[11px] text-rose-600">{errors.driver_full_name}</p>}
          {errors.driver_password && <p className="mt-1 text-[11px] text-rose-600">{errors.driver_password}</p>}
        </div>

        <div className="flex items-center gap-3 pt-1">
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? "Creating…" : "Create Firm"}
          </button>
          {error && <span className="text-sm text-rose-600">{error}</span>}
        </div>
      </form>
    </div>
  );
}
