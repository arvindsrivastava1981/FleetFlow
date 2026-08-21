import { useState } from "react";
import { api } from "../lib/api.js";
import { useToast } from "../context/ToastContext.jsx";

export default function ChangePasswordPage() {
  const toast = useToast();
  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.post("/api/v1/auth/change-password", form);
      toast.success("Password changed successfully.");
      setForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-lg space-y-5">
      <div>
        <h2 className="page-title">Change Password</h2>
        <p className="page-sub">Update the password for your account.</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      <form
        onSubmit={onSubmit}
        className="card-pad space-y-4"
      >
        <div>
          <label className="label">Current Password</label>
          <input
            type="password"
            value={form.current_password}
            onChange={(e) => set("current_password", e.target.value)}
            required
            className="input"
          />
        </div>
        <div>
          <label className="label">New Password</label>
          <input
            type="password"
            value={form.new_password}
            onChange={(e) => set("new_password", e.target.value)}
            required
            minLength={4}
            placeholder="At least 4 characters"
            className="input"
          />
        </div>
        <div>
          <label className="label">Confirm New Password</label>
          <input
            type="password"
            value={form.confirm_password}
            onChange={(e) => set("confirm_password", e.target.value)}
            required
            minLength={4}
            className="input"
          />
        </div>
        <button
          type="submit"
          disabled={busy}
          className="btn-primary w-full"
        >
          {busy ? "Updating…" : "Change Password"}
        </button>
      </form>
    </div>
  );
}