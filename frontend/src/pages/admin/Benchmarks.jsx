import { useEffect, useState } from "react";
import { api } from "../../lib/api.js";

const emptyForm = {
  state_code: "",
  state_name: "",
  benchmark_price_per_liter: "",
  tolerance_pct: "8",
  effective_date: "",
};

export default function BenchmarksPage() {
  const [benchmarks, setBenchmarks] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);

  function load() {
    api
      .get("/api/v1/benchmarks")
      .then(setBenchmarks)
      .catch((e) => setError(e.message));
  }
  useEffect(load, []);

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      const payload = {
        ...form,
        benchmark_price_per_liter: Number(form.benchmark_price_per_liter),
        tolerance_pct: Number(form.tolerance_pct),
        effective_date: form.effective_date || null,
      };
      if (editingId) {
        await api.put(`/api/v1/benchmarks/${editingId}`, payload);
      } else {
        await api.post("/api/v1/benchmarks", payload);
      }
      setForm(emptyForm);
      setEditingId(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(b) {
    if (!window.confirm("Delete this benchmark?")) return;
    try {
      await api.del(`/api/v1/benchmarks/${b.id}`);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  function startEdit(b) {
    setEditingId(b.id);
    setForm({
      state_code: b.state_code,
      state_name: b.state_name,
      benchmark_price_per_liter: String(b.benchmark_price_per_liter),
      tolerance_pct: String(b.tolerance_pct),
      effective_date: b.effective_date || "",
    });
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-extrabold text-slate-900">Fuel Benchmarks</h2>
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl p-4">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <h3 className="text-sm font-extrabold text-slate-800 mb-3">
          {editingId ? "Edit Benchmark" : "Add Benchmark"}
        </h3>
        <form onSubmit={onSubmit} className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <input value={form.state_code} onChange={(e) => set("state_code", e.target.value)} placeholder="State Code (e.g. UP)" required className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.state_name} onChange={(e) => set("state_name", e.target.value)} placeholder="State Name" required className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.benchmark_price_per_liter} onChange={(e) => set("benchmark_price_per_liter", e.target.value)} placeholder="Price ₹/L" required type="number" step="any" className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.tolerance_pct} onChange={(e) => set("tolerance_pct", e.target.value)} placeholder="Tolerance %" type="number" step="any" className="border rounded-lg p-2 bg-slate-50" />
          <input value={form.effective_date} onChange={(e) => set("effective_date", e.target.value)} placeholder="Effective Date (YYYY-MM-DD)" type="date" className="border rounded-lg p-2 bg-slate-50" />
          <div className="col-span-2 md:col-span-4 flex gap-2">
            <button type="submit" className="bg-sky-600 hover:bg-sky-700 text-white font-bold py-2 px-4 rounded-xl transition shadow">
              {editingId ? "Save Changes" : "Add Benchmark"}
            </button>
            {editingId && (
              <button type="button" onClick={() => { setForm(emptyForm); setEditingId(null); }} className="bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-2 px-4 rounded-xl">
                Cancel
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Code</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">State</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Price</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Tolerance</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody>
            {benchmarks.map((b) => (
              <tr key={b.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-3 text-xs font-bold text-slate-800">{b.state_code}</td>
                <td className="p-3 text-xs text-slate-600">{b.state_name}</td>
                <td className="p-3 text-xs text-slate-600">₹{b.benchmark_price_per_liter}</td>
                <td className="p-3 text-xs text-slate-600">{b.tolerance_pct}%</td>
                <td className="p-3 text-xs flex gap-3">
                  <button onClick={() => startEdit(b)} className="text-sky-600 hover:text-sky-800 font-semibold">Edit</button>
                  <button onClick={() => remove(b)} className="text-rose-600 hover:text-rose-800 font-semibold">Delete</button>
                </td>
              </tr>
            ))}
            {!benchmarks.length && (
              <tr>
                <td colSpan="5" className="p-6 text-center text-xs text-slate-400">No benchmarks yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}