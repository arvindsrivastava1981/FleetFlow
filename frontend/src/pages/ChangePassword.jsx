import { useState } from "react";
import { api } from "../lib/api.js";

export default function ChangePasswordPage() {
  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await api.post("/api/v1/auth/change-password", form);
      setMessage("Password changed successfully.");
      setForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4 max-w-lg">
      <div>
        <h2 className="text-lg font-extrabold text-slate-900">Change Password</h2>
        <p className="text-xs text-slate-500">
          Update the password for your account.
        </p>
      </div>

      {message && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm rounded-xl p-4">
          {message}
        </div>
      )}
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">
          {error}
        </div>
      )}

      <form
        onSubmit={onSubmit}
        className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4"
      >
        <div>
          <label className="text-xs font-bold text-slate-700">Current Password</label>
          <input
            type="password"
            value={form.current_password}
            onChange={(e) => set("current_password", e.target.value)}
            required
            className="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-bold text-slate-700">New Password</label>
          <input
            type="password"
            value={form.new_password}
            onChange={(e) => set("new_password", e.target.value)}
            required
            minLength={4}
            placeholder="At least 4 characters"
            className="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"
          />
        </div>
        <div>
          <label className="text-xs font-bold text-slate-700">Confirm New Password</label>
          <input
            type="password"
            value={form.confirm_password}
            onChange={(e) => set("confirm_password", e.target.value)}
            required
            minLength={4}
            className="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={busy}
          className="w-full bg-sky-600 hover:bg-sky-700 text-white font-bold py-2.5 rounded-xl transition shadow disabled:opacity-50"
        >
          {busy ? "Updating…" : "Change Password"}
        </button>
      </form>
    </div>
  );
}