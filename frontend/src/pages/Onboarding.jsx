import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";

// Self-serve firm creation for fleet-less users (e.g. social sign-ups).
// Mirrors the visual language of the login page (brand panel + white form).
export default function OnboardingPage() {
  const { setUser } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [ownerName, setOwnerName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.post("/api/v1/fleets/self-onboard", {
        owner_name: ownerName,
        phone,
        email,
      });
      // Bind the fleet locally so the ProtectedRoute guard lets the user
      // through without waiting for the next /auth/me round-trip.
      setUser((u) => ({ ...u, fleet_id: u.fleet_id ?? -1 }));
      // Refetch the authoritative fleet_id from /me.
      try {
        const me = await api.get("/api/v1/auth/me");
        if (me?.user) setUser(me.user);
      } catch {
        // keep the optimistic binding; /me refreshes on next boot anyway
      }
      toast.success("Your firm is ready — 15-day free trial started!");
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message || "Could not create your firm");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-ink-950 via-brand-900 to-ink-900 p-4 font-sans">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-pop">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-brand-600 to-brand-500 text-sm font-black text-white">
            VK
          </div>
          <div>
            <h1 className="text-lg font-extrabold tracking-tight text-ink-900">
              Set up your firm
            </h1>
            <p className="text-xs text-ink-500">
              One step left — tell us about your transport firm.
            </p>
          </div>
        </div>

        <div className="alert alert-info mb-5">
          Your account doesn&apos;t belong to a firm yet. Create one to start a{" "}
          <strong>15-day free trial</strong> with full access.
        </div>

        {error && <div className="alert alert-error mb-5">{error}</div>}

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="label" htmlFor="owner_name">
              Firm / Owner name
            </label>
            <input
              id="owner_name"
              type="text"
              value={ownerName}
              onChange={(e) => setOwnerName(e.target.value)}
              required
              placeholder="Sharma Transport"
              disabled={busy}
              className="input"
            />
          </div>
          <div>
            <label className="label" htmlFor="phone">
              WhatsApp phone number
            </label>
            <input
              id="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
              placeholder="+91 98765 43210"
              disabled={busy}
              className="input"
            />
          </div>
          <div>
            <label className="label" htmlFor="email">
              Email (optional)
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@firm.in"
              disabled={busy}
              className="input"
            />
          </div>
          <button type="submit" disabled={busy} className="btn-primary w-full">
            {busy ? "Creating your firm…" : "Create firm & start trial"}
          </button>
        </form>
      </div>
    </div>
  );
}
