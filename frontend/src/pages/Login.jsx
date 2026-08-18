import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

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
    <div className="min-h-screen bg-slate-100 p-4 md:p-6 font-sans">
      <div className="max-w-sm mx-auto space-y-6 pt-10">
        <div className="bg-slate-900 text-white p-5 rounded-2xl flex items-center justify-center gap-3 shadow-lg">
          <div className="bg-sky-500 p-2 rounded-xl text-white font-black text-xl">VK</div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight">VahanKhata</h1>
            <p className="text-xs text-sky-400 font-medium">Fleet Expense Verification</p>
          </div>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 w-full max-w-sm space-y-5">
          {error && (
            <p className="text-xs text-rose-600 font-semibold text-center">{error}</p>
          )}
          <form onSubmit={onSubmit} className="space-y-3">
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="Username"
              className="w-full text-sm border rounded-lg p-2.5 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400"
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Password"
              className="w-full text-sm border rounded-lg p-2.5 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400"
            />
            <button
              type="submit"
              disabled={busy}
              className="w-full bg-sky-600 hover:bg-sky-500 text-white font-bold py-2.5 rounded-xl text-sm transition shadow disabled:opacity-50"
            >
              {busy ? "Logging in…" : "Login"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}