import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const FEATURES = [
  "Real-time fuel & expense verification",
  "Built-in rule engine catches anomalies",
  "One-click trip settlement & PDF reports",
  "WhatsApp-style receipt & escalation flow",
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const landing = await login(username, password);
      navigate(landing, { replace: true });
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-ink-950 via-brand-900 to-ink-900 p-4 font-sans">
      <div className="grid w-full max-w-4xl overflow-hidden rounded-2xl bg-white shadow-pop lg:grid-cols-2">
        {/* Brand panel */}
        <div className="hidden flex-col justify-between gap-8 bg-gradient-to-br from-brand-800 to-brand-900 p-10 text-white lg:flex">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 text-lg font-black backdrop-blur">
              VK
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">
                VahanKhata
              </h1>
              <p className="text-sm text-brand-200">
                Fleet Expense Verification &amp; Settlement
              </p>
            </div>
          </div>
          <div>
            <p className="text-lg font-semibold leading-snug">
              Keep every trip honest, fast, and fully accounted.
            </p>
            <ul className="mt-5 space-y-3">
              {FEATURES.map((f) => (
                <li
                  key={f}
                  className="flex items-start gap-2.5 text-sm text-brand-100"
                >
                  <span className="mt-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-xs text-emerald-300">
                    ✓
                  </span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <p className="text-xs text-brand-300">
            © {new Date().getFullYear()} VahanKhata. All rights reserved.
          </p>
        </div>

        {/* Form panel */}
        <div className="flex flex-col justify-center p-8 sm:p-10">
          <div className="mb-6 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-brand-600 to-brand-500 text-sm font-black text-white">
              VK
            </div>
            <div>
              <h1 className="text-lg font-extrabold tracking-tight text-ink-900">
                VahanKhata
              </h1>
              <p className="text-xs text-ink-500">Fleet Expense Verification</p>
            </div>
          </div>

          <h2 className="text-2xl font-bold tracking-tight text-ink-900">
            Sign in
          </h2>
          <p className="mt-1 text-sm text-ink-500">
            Enter your credentials to access your workspace.
          </p>

          {error && <div className="alert alert-error mt-5">{error}</div>}

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label className="label" htmlFor="username">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                placeholder="you@fleet"
                autoComplete="username"
                className="input"
              />
            </div>
            <div>
              <label className="label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                autoComplete="current-password"
                className="input"
              />
            </div>
            <button
              type="submit"
              disabled={busy}
              className="btn-primary w-full"
            >
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}