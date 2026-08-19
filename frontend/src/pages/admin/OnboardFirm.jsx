import { useState } from "react";
import { api } from "../../lib/api.js";

const PLANS = [
  { code: "TRIAL", name: "Trial Pack", desc: "15 days free · 1 vehicle" },
  { code: "MONTHLY", name: "Monthly", desc: "₹799 · 1 vehicle · month" },
  { code: "YEARLY", name: "Yearly", desc: "₹7,191 · 1 vehicle · year (25% off)" },
];

export default function OnboardFirmPage() {
  const [form, setForm] = useState({
    owner_name: "", phone: "", email: "",
    username: "", full_name: "", password: "", plan_code: "TRIAL",
    vehicle_number: "", make_model: "",
    driver_username: "", driver_full_name: "", driver_password: "", driver_phone: "",
  });
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const input = "input";

  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    const payload = {
      fleet: { owner_name: form.owner_name, phone: form.phone, email: form.email || null },
      owner: { username: form.username, full_name: form.full_name, password: form.password, email: form.email || null },
      plan_code: form.plan_code,
    };
    if (form.vehicle_number) {
      payload.initial_vehicle = { vehicle_number: form.vehicle_number, make_model: form.make_model || null };
    }
    if (form.driver_username && form.driver_full_name && form.driver_password) {
      payload.initial_driver = {
        username: form.driver_username, full_name: form.driver_full_name,
        password: form.driver_password, phone: form.driver_phone || null,
      };
    }
    try {
      const data = await api.post("/api/v1/fleets/onboard", payload);
      setResult(data);
    } catch (err) {
      setError(err.message);
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
          {result.payment_url && (
            <p>Payment link: <a className="underline text-emerald-700" href={result.payment_url} target="_blank" rel="noreferrer">open checkout</a></p>
          )}
        </div>
      )}

      <form onSubmit={onSubmit} className="card-pad space-y-4">
        <div><h3 className="text-sm font-extrabold text-slate-800 mb-2">Firm details</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
            <input value={form.owner_name} onChange={(e) => set("owner_name", e.target.value)} placeholder="Owner / Firm Name" required className={input} />
            <input value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="Phone" required className={input} />
            <input value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="Email" className={input} />
          </div></div>

        <div><h3 className="text-sm font-extrabold text-slate-800 mb-2">Owner / Trip Manager account</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
            <input value={form.username} onChange={(e) => set("username", e.target.value)} placeholder="Username" required className={input} />
            <input value={form.full_name} onChange={(e) => set("full_name", e.target.value)} placeholder="Full Name" required className={input} />
            <input value={form.password} onChange={(e) => set("password", e.target.value)} placeholder="Temporary Password" required type="password" className={input} />
          </div></div>

        <div><h3 className="text-sm font-extrabold text-slate-800 mb-2">Subscription</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm">
            {PLANS.map((p) => (
              <label key={p.code} className={`cursor-pointer rounded-xl border p-3 ${form.plan_code === p.code ? "border-brand-500 bg-brand-50" : "border-ink-200"}`}>
                <input type="radio" name="plan_code" value={p.code} checked={form.plan_code === p.code} onChange={(e) => set("plan_code", e.target.value)} className="mr-2" />
                <span className="font-bold">{p.name}</span>
                <span className="block text-[10px] text-slate-500">{p.desc}</span>
              </label>
            ))}
          </div></div>

        <div><h3 className="text-sm font-extrabold text-slate-800 mb-2">Optional first vehicle</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <input value={form.vehicle_number} onChange={(e) => set("vehicle_number", e.target.value)} placeholder="Vehicle Number (e.g. UP32TA1234)" className={input} />
            <input value={form.make_model} onChange={(e) => set("make_model", e.target.value)} placeholder="Make / Model" className={input} />
          </div></div>

        <div><h3 className="text-sm font-extrabold text-slate-800 mb-2">Optional first driver</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <input value={form.driver_username} onChange={(e) => set("driver_username", e.target.value)} placeholder="Driver Username" className={input} />
            <input value={form.driver_full_name} onChange={(e) => set("driver_full_name", e.target.value)} placeholder="Driver Full Name" className={input} />
            <input value={form.driver_password} onChange={(e) => set("driver_password", e.target.value)} placeholder="Driver Password" type="password" className={input} />
            <input value={form.driver_phone} onChange={(e) => set("driver_phone", e.target.value)} placeholder="Driver Phone" className={input} />
          </div></div>

        <button type="submit" className="btn-primary">Create Firm</button>
      </form>
    </div>
  );
}
