import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";

const FEATURES = [
  "Real-time fuel & expense verification",
  "Built-in rule engine catches anomalies",
  "One-click trip settlement & PDF reports",
  "WhatsApp-style receipt & escalation flow",
];

// Show the "server waking up" reassurance after this many seconds. Render's
// free tier spins the API down when idle and a cold start can take ~50s, so
// the UI must explain the wait instead of looking frozen.
const COLD_START_HINT_AFTER_S = 8;

// Marketing site origin (mirrors VITE_APP_URL on the public site, which links
// back here). Overridable at build time; defaults to the production domain.
const PUBLIC_SITE_URL = import.meta.env.VITE_SITE_URL || "https://vahankhata.in";

function ButtonSpinner() {
  return (
    <svg
      className="h-4 w-4 shrink-0 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

export default function LoginPage() {
  const { login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  // Seconds since the sign-in request started — powers the live counter and
  // the cold-start hint so a slow first login doesn't feel like a hang.
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!busy) return undefined;
    setElapsed(0);
    const startedAt = Date.now();
    const id = setInterval(
      () => setElapsed(Math.floor((Date.now() - startedAt) / 1000)),
      1000,
    );
    return () => clearInterval(id);
  }, [busy]);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const landing = await login(username, password);
      navigate(landing, { replace: true });
    } catch (err) {
      // A dropped/timed-out fetch surfaces as "Failed to fetch" — during a
      // cold start that almost always means the server was still waking up.
      const message =
        err.message === "Failed to fetch"
          ? "Couldn't reach the server. It may still be waking up — please try again in a minute."
          : err.message || "Login failed";
      setError(message);
      toast.error(message);
    } finally {
      setBusy(false);
      setElapsed(0);
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
            © {new Date().getFullYear()} VahanKhata. All rights reserved. ·{" "}
            <a
              href={PUBLIC_SITE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-brand-200 underline-offset-2 transition hover:text-white hover:underline"
            >
              vahankhata.in ↗
            </a>
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
                disabled={busy}
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
                disabled={busy}
                className="input"
              />
            </div>
            <button
              type="submit"
              disabled={busy}
              className="btn-primary w-full"
            >
              {busy ? (
                <span className="inline-flex items-center justify-center gap-2">
                  <ButtonSpinner />
                  <span>Signing in…</span>
                  {elapsed > 0 && (
                    <span className="tabular-nums opacity-80">
                      {elapsed}s
                    </span>
                  )}
                </span>
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          {busy && elapsed >= COLD_START_HINT_AFTER_S && (
            <div className="alert alert-info mt-4">
              Still connecting — our free-tier server sleeps when idle and can
              take up to a minute to wake up on the first sign-in. Keep this
              tab open; you&apos;ll be signed in automatically once it
              responds.
            </div>
          )}

          <p className="mt-6 text-center text-xs text-ink-400">
            Learn more at{" "}
            <a
              href={PUBLIC_SITE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-brand-600 underline-offset-2 transition hover:text-brand-700 hover:underline"
            >
              vahankhata.in ↗
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}