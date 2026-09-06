import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { BrandMark } from "../components/Logo.jsx";

// Self-serve onboarding wizard for fleet-less users (e.g. social sign-ups).
// Step 1: firm (creates TRIAL fleet + binds caller as owner) - required.
// Step 2: first vehicle (optional) -> POST /api/v1/vehicles
// Step 3: first driver (optional)  -> POST /api/v1/drivers
const STEPS = ["Firm", "Vehicle", "Driver"];
const SUBTITLES = [
  "Set up your transport firm and start your free trial.",
  "Register the first vehicle in your fleet - you can skip for now.",
  "Invite your first driver - you can add more later.",
];
const PLATE_RE = /^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$/;
const BATTA_TYPES = [
  { value: "FIXED_TRIP", label: "Fixed per trip" },
  { value: "PER_KM", label: "Per kilometre" },
  { value: "DAILY", label: "Daily" },
  { value: "NONE", label: "None" },
];

export default function OnboardingPage() {
  const { setUser } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Step 1 - firm
  const [ownerName, setOwnerName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  // Step 2 - vehicle (optional)
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [makeModel, setMakeModel] = useState("");
  // Step 3 - driver (optional)
  const [driverEmail, setDriverEmail] = useState("");
  const [driverName, setDriverName] = useState("");
  const [driverPassword, setDriverPassword] = useState("");
  const [driverPhone, setDriverPhone] = useState("");
  const [battaType, setBattaType] = useState("FIXED_TRIP");
  const [battaRate, setBattaRate] = useState("");

  async function run(fn, successMsg) {
    setError("");
    setBusy(true);
    try {
      await fn();
      if (successMsg) toast.success(successMsg);
      return true;
    } catch (err) {
      setError(err.message || "Something went wrong");
      return false;
    } finally {
      setBusy(false);
    }
  }

  function finish() {
    toast.success("You're all set - welcome to VahanKhata.in!");
    navigate("/dashboard", { replace: true });
  }

  async function submitFirm(e) {
    e.preventDefault();
    if (!ownerName.trim() || !phone.trim()) {
      setError("Owner name and phone are required.");
      return;
    }
    const ok = await run(async () => {
      const res = await api.post("/api/v1/fleets/self-onboard", {
        owner_name: ownerName.trim(),
        phone: phone.trim(),
        email: email.trim() || null,
      });
      // Refresh auth user so ProtectedRoute stops redirecting to /onboarding.
      const me = await api.get("/api/v1/auth/me");
      setUser(me);
      return res;
    }, "Firm created - 15-day trial started.");
    if (ok) setStep(1);
  }

  async function submitVehicle(e) {
    e.preventDefault();
    if (!vehicleNumber.trim()) return setStep(2); // left blank = skip
    if (!PLATE_RE.test(vehicleNumber.trim().toUpperCase())) {
      setError("Enter a valid plate, e.g. UP32TA1234.");
      return;
    }
    const ok = await run(async () => {
      await api.post("/api/v1/vehicles", {
        vehicle_number: vehicleNumber.trim().toUpperCase(),
        make_model: makeModel || null,
        tank_capacity_liters: 350.0,
        expected_km_per_liter: 4.0,
      });
    }, "Vehicle added.");
    if (ok) setStep(2);
  }

  async function submitDriver(e) {
    e.preventDefault();
    const allEmpty = !driverEmail.trim() && !driverName.trim() && !driverPassword.trim();
    if (allEmpty) return finish();
    if (!driverEmail.trim() || !driverName.trim() || !driverPassword.trim()) {
      setError("Fill all driver fields (email, name and password), or clear them to skip.");
      return;
    }
    const ok = await run(async () => {
      await api.post("/api/v1/drivers", {
        email: driverEmail.trim(),
        full_name: driverName.trim(),
        password: driverPassword,
        phone: driverPhone || null,
        batta_type: battaType,
        default_batta_rate:
          battaType === "NONE" ? 0 : battaRate ? Number(battaRate) : null,
      });
    }, "Driver added.");
    if (ok) finish();
  }

  return (
    <div className="grid min-h-screen font-sans lg:grid-cols-[420px_1fr]">
      {/* Brand / progress panel (desktop) */}
      <div className="hidden flex-col justify-between bg-gradient-to-b from-brand-800 to-brand-900 p-10 text-white lg:flex">
        <div className="flex items-center gap-3">
          <BrandMark className="h-10 w-10" tileClassName="bg-white/15 backdrop-blur" />
          <div>
            <p className="text-base font-extrabold tracking-tight">
              VahanKhata<span className="text-brand-200">.in</span>
            </p>
            <p className="text-xs text-white/60">Fleet Expense Verification</p>
          </div>
        </div>
        <div className="space-y-6">
          <h2 className="text-2xl font-extrabold leading-snug">
            Get your firm on the road in 3 quick steps.
          </h2>
          <ol className="space-y-4">
            {STEPS.map((label, i) => (
              <li key={label} className="flex items-start gap-3">
                <span
                  className={
                    "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold " +
                    (i < step
                      ? "bg-white text-brand-800"
                      : i === step
                        ? "bg-white/20 ring-2 ring-white"
                        : "bg-white/10 text-white/60")
                  }
                >
                  {i < step ? "OK" : i + 1}
                </span>
                <div>
                  <p className={"text-sm font-bold " + (i <= step ? "text-white" : "text-white/60")}>
                    {label === "Firm" ? "Create your firm" : "Add a " + label.toLowerCase()}
                  </p>
                  <p className="text-xs text-white/60">
                    {i === 0 && "Required - starts your 15-day free trial"}
                    {i === 1 && "Optional - your trips need at least one"}
                    {i === 2 && "Optional - invite them via WhatsApp later"}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
        <p className="text-xs text-white/50">Learn more at vahankhata.in</p>
      </div>

      {/* Form card */}
      <div className="flex items-center justify-center bg-ink-50 p-4 sm:p-8">
        <div className="w-full max-w-md rounded-2xl bg-white p-7 shadow-pop sm:p-9">
          {/* Mobile progress */}
          <div className="mb-6 lg:hidden">
            <div className="flex items-center gap-2">
              {STEPS.map((label, i) => (
                <span
                  key={label}
                  className={
                    "h-1.5 flex-1 rounded-full " +
                    (i < step ? "bg-brand-600" : i === step ? "bg-brand-400" : "bg-ink-200")
                  }
                />
              ))}
            </div>
            <p className="mt-2 text-xs font-semibold text-ink-500">
              Step {step + 1} of 3 - {STEPS[step]}
            </p>
          </div>

          <h1 className="text-xl font-extrabold tracking-tight text-ink-900">
            {step === 0 && "Create your firm"}
            {step === 1 && "Add your first vehicle"}
            {step === 2 && "Add your first driver"}
          </h1>
          <p className="mt-1 text-sm text-ink-500">{SUBTITLES[step]}</p>

          {error && <div className="alert alert-error mt-5">{error}</div>}

          {step === 0 && (
            <form onSubmit={submitFirm} className="mt-6 space-y-4">
              <div>
                <label className="label" htmlFor="owner_name">Firm / Owner name</label>
                <input id="owner_name" type="text" value={ownerName}
                  onChange={(e) => setOwnerName(e.target.value)} required
                  placeholder="Sharma Transport" disabled={busy} className="input" autoFocus />
              </div>
              <div>
                <label className="label" htmlFor="phone">WhatsApp phone number</label>
                <input id="phone" type="tel" value={phone}
                  onChange={(e) => setPhone(e.target.value)} required
                  placeholder="+91 98765 43210" disabled={busy} className="input" />
              </div>
              <div>
                <label className="label" htmlFor="email">Email (optional)</label>
                <input id="email" type="email" value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@firm.in" disabled={busy} className="input" />
              </div>
              <button type="submit" disabled={busy} className="btn-primary w-full">
                {busy ? "Creating your firm..." : "Create firm & continue"}
              </button>
            </form>
          )}


          {step === 1 && (
            <form onSubmit={submitVehicle} className="mt-6 space-y-4">
              <div>
                <label className="label" htmlFor="vehicle_number">Vehicle number (plate)</label>
                <input id="vehicle_number" type="text" value={vehicleNumber}
                  onChange={(e) => setVehicleNumber(e.target.value.toUpperCase())}
                  placeholder="UP32TA1234" disabled={busy} className="input" autoFocus />
              </div>
              <div>
                <label className="label" htmlFor="make_model">Make / model (optional)</label>
                <input id="make_model" type="text" value={makeModel}
                  onChange={(e) => setMakeModel(e.target.value)}
                  placeholder="Tata 407, 2019" disabled={busy} className="input" />
              </div>
              <p className="text-xs text-ink-400">
                Tank capacity and mileage start at the defaults (350 L / 4 km/L) -
                editable later on the Vehicles page.
              </p>
              <div className="flex gap-3">
                <button type="button" onClick={() => setStep(2)} disabled={busy}
                  className="btn-secondary flex-1">Skip for now</button>
                <button type="submit" disabled={busy} className="btn-primary flex-1">
                  {busy ? "Adding..." : "Add vehicle"}
                </button>
              </div>
            </form>
          )}


          {step === 2 && (
            <form onSubmit={submitDriver} className="mt-6 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label" htmlFor="driver_email">Email</label>
                  <input id="driver_email" type="email" value={driverEmail}
                    onChange={(e) => setDriverEmail(e.target.value)}
                    placeholder="driver@example.com" disabled={busy} className="input" autoFocus />
                </div>
                <div>
                  <label className="label" htmlFor="driver_name">Full name</label>
                  <input id="driver_name" type="text" value={driverName}
                    onChange={(e) => setDriverName(e.target.value)}
                    placeholder="Ramesh Kumar" disabled={busy} className="input" />
                </div>
              </div>
              <div>
                <label className="label" htmlFor="driver_password">Temporary password</label>
                <input id="driver_password" type="text" value={driverPassword}
                  onChange={(e) => setDriverPassword(e.target.value)}
                  placeholder="Share it with the driver" disabled={busy} className="input" />
              </div>
              <div>
                <label className="label" htmlFor="driver_phone">Phone (optional)</label>
                <input id="driver_phone" type="tel" value={driverPhone}
                  onChange={(e) => setDriverPhone(e.target.value)}
                  placeholder="+91 98765 43210" disabled={busy} className="input" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label" htmlFor="batta_type">Batta type</label>
                  <select id="batta_type" value={battaType}
                    onChange={(e) => setBattaType(e.target.value)} disabled={busy}
                    className="input">
                    {BATTA_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="batta_rate">Batta rate</label>
                  <input id="batta_rate" type="number" min="0" step="0.01"
                    value={battaRate} disabled={busy || battaType === "NONE"}
                    onChange={(e) => setBattaRate(e.target.value)}
                    placeholder="2500" className="input" />
                </div>
              </div>
              <div className="flex gap-3">
                <button type="button" onClick={finish} disabled={busy}
                  className="btn-secondary flex-1">Skip & finish</button>
                <button type="submit" disabled={busy} className="btn-primary flex-1">
                  {busy ? "Adding..." : "Add driver & finish"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
