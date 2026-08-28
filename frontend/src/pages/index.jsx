import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import SocialLogin from "../components/SocialLogin.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";

const FEATURES = [
  "Real-time fuel & expense verification",
  "Built-in rule engine catches anomalies",
  "One-click trip settlement & PDF reports",
  "WhatsApp-style receipt & escalation flow",
];
const COLD_START_HINT_AFTER_S = 8;
const PUBLIC_SITE_URL = import.meta.env.VITE_SITE_URL || "https://vahankhata.in";

function ButtonSpinner() {
  return (
    <svg className="h-4 w-4 shrink-0 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );
}

function TabBar({ tab, setTab }) {
  return (
    <div className="mb-6 flex rounded-lg bg-ink-100 p-0.5">
      {["signin", "signup"].map((t) => (
        <button key={t} type="button" onClick={() => setTab(t)}
          className={"flex-1 rounded-md px-4 py-2 text-sm font-semibold transition " +
            (tab === t ? "bg-white text-ink-900 shadow-sm" : "text-ink-500 hover:text-ink-700")}>
          {t === "signin" ? "Sign in" : "Create account"}
        </button>
      ))}
    </div>
  );
}
function SignInForm({ busy, elapsed, onSubmit, username, setUsername, password, setPassword }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label className="label" htmlFor="username">Username</label>
        <input id="username" type="text" value={username}
          onChange={(e) => setUsername(e.target.value)} required
          placeholder="you@fleet" autoComplete="username"
          disabled={busy} className="input" />
      </div>
      <div>
        <label className="label" htmlFor="password">Password</label>
        <input id="password" type="password" value={password}
          onChange={(e) => setPassword(e.target.value)} required
          placeholder="........" autoComplete="current-password"
          disabled={busy} className="input" />
      </div>
      <button type="submit" disabled={busy} className="btn-primary w-full">
        {busy ? (
          <span className="inline-flex items-center justify-center gap-2">
            <ButtonSpinner /><span>Signing in...</span>
            {elapsed > 0 && <span className="tabular-nums opacity-80">{elapsed}s</span>}
          </span>
        ) : "Sign in"}
      </button>
    </form>
  );
}

function SignUpForm({ busy, onSubmit, signup, setSignup }) {
  const s = (k, v) => setSignup((p) => ({ ...p, [k]: v }));
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label className="label" htmlFor="su_email">Email</label>
        <input id="su_email" type="email" value={signup.email}
          onChange={(e) => s("email", e.target.value)} required
          placeholder="you@example.com" autoComplete="email"
          disabled={busy} className="input" />
      </div>
      <div>
        <label className="label" htmlFor="su_password">Password (min 8 characters)</label>
        <input id="su_password" type="password" value={signup.password}
          onChange={(e) => s("password", e.target.value)} required
          placeholder="........" autoComplete="new-password"
          disabled={busy} className="input" />
      </div>
      <div>
        <label className="label" htmlFor="su_confirm">Confirm password</label>
        <input id="su_confirm" type="password" value={signup.confirmPassword}
          onChange={(e) => s("confirmPassword", e.target.value)} required
          placeholder="........" autoComplete="new-password"
          disabled={busy} className="input" />
      </div>
      <p className="text-xs text-ink-400">
        Your username and display name will be set from your email address. You can change them later in Settings.
      </p>
      <button type="submit" disabled={busy} className="btn-primary w-full">
        {busy ? "Creating your account..." : "Create account"}
      </button>
    </form>
  );
}

export default function LoginPage() {
  const { login, register } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [tab, setTab] = useState("signin");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const emptySignup = { email: "", password: "", confirmPassword: "" };
  const [signup, setSignup] = useState(emptySignup);
  const [signupDone, setSignupDone] = useState("");

  // Handle ?verified= query param from email verification redirect.
  const [searchParams, setSearchParams] = useSearchParams();
  const verifiedFlag = searchParams.get("verified");
  useEffect(() => {
    if (!verifiedFlag) return;
    if (verifiedFlag === "1") {
      setTab("signin");
      toast.success("Email verified - you can now sign in.");
    } else if (verifiedFlag === "invalid") {
      setTab("signin");
      setError("Verification link expired or invalid. Please sign up again.");
    }
    // Remove the flag from the URL so the message doesn't reappear on refresh.
    searchParams.delete("verified");
    setSearchParams(searchParams, { replace: true });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!busy) return undefined;
    setElapsed(0);
    const startedAt = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(id);
  }, [busy]);

  async function doSignin(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const landing = await login(username, password);
      navigate(landing, { replace: true });
    } catch (err) {
      let msg = err.message || "Login failed";
      if (err.message === "Failed to fetch")
        msg = "Couldn't reach the server. It may still be waking up.";
      if (err.code === "EMAIL_UNVERIFIED")
        msg = "Email not verified yet. Check your inbox.";
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
      setElapsed(0);
    }
  }

  async function doSignup(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const msg = await register(
        signup.email, signup.password, signup.confirmPassword,
      );
      setSignupDone(msg);
      setSignup(emptySignup);
      toast.success(msg);
    } catch (err) {
      setError(err.message || "Registration failed");
    } finally {
      setBusy(false);
      setElapsed(0);
    }
  }

  const B = (
    <div className="hidden flex-col justify-between gap-8 bg-gradient-to-br from-brand-800 to-brand-900 p-10 text-white lg:flex">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 text-lg font-black backdrop-blur">VK</div>
        <div>
          <h1 className="text-xl font-extrabold tracking-tight">VahanKhata</h1>
          <p className="text-xs text-white/60">Fleet Expense Verification</p>
        </div>
      </div>
      <div className="space-y-8">
        <h2 className="text-2xl font-extrabold leading-relaxed">Start tracking your fleet expenses in minutes.</h2>
        <ul className="space-y-3">
          {FEATURES.map((f) => (
            <li key={f} className="flex items-start gap-2 text-sm text-white/80">
              <span className="mt-0.5 text-brand-200 font-bold">+</span>{f}
            </li>
          ))}
        </ul>
      </div>
      <p className="text-xs text-white/40">Learn more at vahankhata.in</p>
    </div>
  );
return (
    <div className="flex min-h-screen bg-gradient-to-br from-ink-950 via-brand-900 to-ink-900 p-4">
      <div className="mx-auto grid w-full max-w-4xl overflow-hidden rounded-2xl bg-white shadow-pop my-auto lg:grid-cols-2">
        {B}
        <div className="flex items-center justify-center bg-ink-50 p-6 sm:p-8 lg:p-10">
          <div className="w-full max-w-sm rounded-2xl bg-white p-7 shadow-pop sm:p-9">
            <div className="mb-6 flex items-center gap-3 lg:hidden">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-brand-600 to-brand-500 text-sm font-black text-white">VK</div>
              <div>
                <h1 className="text-lg font-extrabold tracking-tight text-ink-900">VahanKhata</h1>
                <p className="text-xs text-ink-500">Fleet Expense Verification</p>
              </div>
            </div>
            <TabBar tab={tab} setTab={setTab} />
            {error && <div className="alert alert-error mb-5">{error}</div>}
            {signupDone && tab === "signup" && <div className="alert alert-info mb-5">{signupDone}</div>}
            {tab === "signin" && (
              <>
                <h2 className="text-xl font-bold tracking-tight text-ink-900">Sign in</h2>
                <p className="mt-1 text-sm text-ink-500">Enter your credentials to access your workspace.</p>
                <div className="mt-5">
                  <SignInForm busy={busy} elapsed={elapsed} onSubmit={doSignin}
                    username={username} setUsername={setUsername}
                    password={password} setPassword={setPassword} />
                </div>
              </>
            )}
            {tab === "signup" && (
              <>
                <h2 className="text-xl font-bold tracking-tight text-ink-900">Create your account</h2>
                <p className="mt-1 text-sm text-ink-500">Get started with a free 15-day trial. No credit card needed.</p>
                <div className="mt-5">
                  <SignUpForm busy={busy} onSubmit={doSignup}
                    signup={signup} setSignup={setSignup} />
                </div>
              </>
            )}
            <div className="mt-5">
              <SocialLogin busy={busy} />
            </div>
            {busy && elapsed >= COLD_START_HINT_AFTER_S && (
              <div className="alert alert-info mt-4">
                Still connecting - our server sleeps when idle and can take up to a minute to wake up. Keep this tab open.
              </div>
            )}
            <p className="mt-6 text-center text-xs text-ink-400">
              Learn more at{" "}
              <a href={PUBLIC_SITE_URL} target="_blank" rel="noopener noreferrer"
                className="font-semibold text-brand-600 underline-offset-2 transition hover:text-brand-700 hover:underline">
                vahankhata.in
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
