import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { useShortcuts } from "../context/ShortcutContext.jsx";
import Loader from "../components/Loader.jsx";
import useUnsavedGuard, { LeaveGuardDialog } from "../hooks/useUnsavedGuard.jsx";

// Expense types with icons
const TYPES = [
  { code: "FUEL", label: "Diesel", icon: "⛽" },
  { code: "DEF", label: "AdBlue", icon: "🔵" },
  { code: "TOLL", label: "Toll", icon: "🛣️" },
  { code: "REPAIR", label: "Repair", icon: "🔧" },
  { code: "CHALLAN", label: "Challan", icon: "👮" },
  { code: "MISC", label: "Misc", icon: "📝" },
  { code: "GOODS_BUY", label: "Goods Buy", icon: "📦" },
  { code: "GOODS_SALE", label: "Goods Sale", icon: "💰" },
  { code: "CASH_ADVANCE", label: "Advance", icon: "💵" },
  { code: "DRIVER_SALARY", label: "Batta", icon: "🧑‍✈️" },
];

const FUELISH = new Set(["FUEL", "DEF"]);
const PRESET_KEY = "vk_amount_presets";

// Shortcuts for this page - displayed in header
const PAGE_SHORTCUTS = [
  { keys: ["Enter"], label: "save & add another" },
  { keys: ["1–9", "0"], label: "pick type" },
  { keys: ["Ctrl", "Enter"], label: "save & finish" },
  { keys: ["Ctrl", "Z"], label: "undo last" },
];

function loadPresets() {
  try {
    return JSON.parse(localStorage.getItem(PRESET_KEY) || "{}");
  } catch {
    return {};
  }
}

function rememberAmount(type, amount) {
  if (!amount || amount <= 0) return;
  try {
    const all = loadPresets();
    const list = [amount, ...(all[type] || [])].filter(
      (v, i, a) => a.indexOf(v) === i,
    );
    all[type] = list.slice(0, 3);
    localStorage.setItem(PRESET_KEY, JSON.stringify(all));
  } catch {
    /* storage unavailable — presets are polish, never blocking */
  }
}

export default function TripDetailPage() {
  const { tripCode } = useParams();
  const { user } = useAuth();
  const toast = useToast();
  const { setShortcuts } = useShortcuts();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [type, setType] = useState("FUEL");
  const [amount, setAmount] = useState("");
  const [liters, setLiters] = useState("");
  const [odometer, setOdometer] = useState("");
  const [stateCode, setStateCode] = useState("");
  const [note, setNote] = useState("");
  const [stationName, setStationName] = useState("");
  const [settleOdo, setSettleOdo] = useState("");
  const [busy, setBusy] = useState(false);
  const [settleBusy, setSettleBusy] = useState(false);
  const [savedExpense, setSavedExpense] = useState(null); // {id, label} for Undo
  const [states, setStates] = useState([]);
  const saveRef = useRef();
  const skipRef = useRef(false);
  const dirty = Boolean(amount || liters || odometer || note || stationName);
  const blocker = useUnsavedGuard(dirty, skipRef);

  // Set shortcuts for this page in the header
  useEffect(() => {
    setShortcuts(PAGE_SHORTCUTS);
    return () => setShortcuts([]);
  }, [setShortcuts]);

  // Auto-dismiss the Undo snackbar after a short window.
  useEffect(() => {
    if (!savedExpense) return undefined;
    const t = setTimeout(() => setSavedExpense(null), 9000);
    return () => clearTimeout(t);
  }, [savedExpense]);

  async function undoLast() {
    if (!savedExpense) return;
    try {
      await api.del(`/api/v1/expenses/${savedExpense.id}`);
      toast.success("Expense undone.");
      setSavedExpense(null);
      load();
    } catch (err) {
      toast.error(err.message);
      setSavedExpense(null);
    }
  }

  function load() {
    setError("");
    api
      .get(`/api/v1/trips/${tripCode}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }

  useEffect(load, [tripCode]);

  // Load fueling states
  useEffect(() => {
    api.get("/api/v1/states?source=benchmarks").then(setStates).catch(() => {});
  }, []);

  // Fueling-state preselection
  useEffect(() => {
    if (stateCode) return;
    const fav = states.find((s) => s.is_favorite === true);
    setStateCode(fav?.code || "UP");
  }, [states, stateCode]);

  // Keyboard data-entry shortcuts:
  //  - Enter in any expense field → Save & Add Another.
  //  - Ctrl+Enter → Save & Finish.
  //  - Ctrl+Z → Undo last expense.
  //  - Digit keys 1-9, 0 (while no field is focused) → pick expense type by
  //    position (1=Diesel … 0=last) and jump to the amount field.
  useEffect(() => {
    const ENTER_SAVE_IDS = new Set([
      "ee-amount", "ee-liters", "ee-odo", "ee-station", "ee-note",
    ]);
    function onKey(e) {
      const el = e.target;

      // Ctrl+Z → Undo last expense
      if (e.ctrlKey && e.key.toLowerCase() === "z") {
        e.preventDefault();
        undoLast();
        return;
      }

      if (e.key === "Enter") {
        if (el && ENTER_SAVE_IDS.has(el.id) && !busy) {
          e.preventDefault();
          // Ctrl+Enter → Save & Finish, Enter → Save & Add Another
          saveRef.current(e.ctrlKey ? false : true);
        }
        return;
      }
            const activeEl = document.activeElement || el;
      const isControl =
        activeEl &&
        (activeEl.tagName === "INPUT" ||
          activeEl.tagName === "SELECT" ||
          activeEl.tagName === "TEXTAREA" ||
          activeEl.tagName === "BUTTON");
      if (!isControl && /^[0-9]$/.test(e.key)) {
        const idx = e.key === "0" ? TYPES.length - 1 : Number(e.key) - 1;
        if (idx >= 0 && idx < TYPES.length) {
          e.preventDefault();
          setType(TYPES[idx].code);
          document.getElementById("ee-amount")?.focus();
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, tripCode]);

  async function save(again) {
    if (!amount || Number(amount) <= 0) {
      toast.error("Enter the amount first.");
      return;
    }
    setBusy(true);
    saveRef.current = save;
    try {
      const res = await api.post("/api/v1/expenses", {
        trip_code: tripCode,
        exp_type: type,
        amount: Number(amount),
        liters: FUELISH.has(type) ? Number(liters || 0) : undefined,
        odometer: Number(odometer || 0),
        ...(FUELISH.has(type) && stateCode ? { state_code: stateCode } : {}),
        ...(FUELISH.has(type) && stationName.trim()
          ? { station_name: stationName.trim() }
          : {}),
        ...(note.trim() ? { raw_receipt_text: note.trim() } : {}),
      });
      rememberAmount(type, Number(amount));
      if (res?.expense_id) {
        setSavedExpense({ id: res.expense_id, label: `${type} ₹${amount}` });
      }
      toast.success(`${type} ₹${amount} saved.`);
      if (again) {
        setAmount("");
        setNote("");
        document.getElementById("ee-amount")?.focus();
      } else {
        skipRef.current = true;
        load();
      }
      load();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function settleTrip() {
    const endOdo = Number(settleOdo || 0);
    const startOdo = Number(trip?.start_odo);
    if (startOdo && endOdo && endOdo < startOdo) {
      toast.error(
        `End odometer (${endOdo}) is below the trip start (${startOdo}) — check it.`,
      );
      return;
    }
    setSettleBusy(true);
    setError("");
    try {
      await api.post(`/api/v1/trips/${tripCode}/settle`, {
        end_odo: endOdo,
      });
      setSettleOdo("");
      toast.success("Trip settled. 🤝");
      skipRef.current = true;
      load();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setSettleBusy(false);
    }
  }

  const trip = data?.trip;
  const expenses = data?.expenses || [];
  const s = trip?.settlement;
  const canSettle =
    user?.role === "trip_manager" || user?.role === "super_admin";
  const showSettle =
    canSettle &&
    (trip?.status === "ACTIVE" || trip?.status === "COMPLETED");

  const presets = useMemo(() => loadPresets()[type] || [], [type, amount]);
  const needsFuelFields = FUELISH.has(type);

  function dueBadge() {
    if (!s || s.net_balance === 0) return null;
    if (s.is_driver_refund) {
      return (
        <span className="badge bg-amber-100 text-amber-700">
          Refundable to Fleet
        </span>
      );
    }
    return (
      <span className="badge bg-emerald-100 text-emerald-700">
        Payable to Driver
      </span>
    );
  }

  const sortedStates = [...states].sort(
    (a, b) =>
      Number(b.is_favorite === true) - Number(a.is_favorite === true) ||
      String(a.name).localeCompare(String(b.name)),
  );

  return (
    <div className="space-y-4">
      <h2 className="page-title">
        Trip {tripCode}
        {trip && (
          <span className="ml-2 text-xs font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 align-middle">
            {trip.status}
          </span>
        )}
      </h2>
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {!data && !error && <Loader label="Loading trip…" full />}

      {showSettle && (
        <div className="card p-4 space-y-3">
          <div>
            <p className="text-xs font-extrabold text-slate-800">
              Ready to settle this trip?
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              All expenses must be APPROVED or REJECTED first. Settling closes the trip and locks the settlement ledger.
            </p>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[140px]">
              <label
                htmlFor="end_odo"
                className="block text-[10px] font-bold text-slate-500 uppercase mb-1"
              >
                Closing Odometer (KM)
              </label>
              <input
                id="end_odo"
                type="number"
                step="any"
                min={trip?.start_odo ?? 0}
                value={settleOdo}
                onChange={(e) => setSettleOdo(e.target.value)}
                placeholder={`Min: ${trip?.start_odo ?? 0}`}
                className="input text-sm w-full"
                required
              />
            </div>
            <button
              onClick={settleTrip}
              disabled={settleBusy || !settleOdo}
              className="btn-success px-4 py-2 rounded-xl transition shadow disabled:opacity-50"
            >
              {settleBusy ? "Settling…" : "✓ Settle Trip"}
            </button>
          </div>
        </div>
      )}

      {s && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="card p-4">
            <p className="text-[10px] font-bold text-slate-400 uppercase">Owner Cash In</p>
            <p className="page-title mt-1">
              ₹{(s.advance_amount ?? 0).toLocaleString("en-IN")}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-[10px] font-bold text-slate-400 uppercase">Approved Road Spend</p>
            <p className="page-title mt-1">
              ₹{(s.total_road_expenses ?? 0).toLocaleString("en-IN")}
            </p>
          </div>
          <div className="card p-4">
            <p className="text-[10px] font-bold text-slate-400 uppercase">Driver Salary</p>
            <p className="page-title mt-1">
              ₹{(s.driver_batta ?? 0).toLocaleString("en-IN")}
            </p>
          </div>
          <div className="card p-4">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-bold text-slate-400 uppercase">Final Settlement</p>
              {dueBadge()}
            </div>
            <p className="page-title mt-1">
              ₹{Math.abs(s.net_balance ?? 0).toLocaleString("en-IN")}
            </p>
            <p className="text-[10px] font-bold text-slate-500 mt-1 uppercase">{s.status_label_en}</p>
          </div>
        </div>
      )}

      {/* Expense Entry Section */}
      <div className="card p-4 space-y-4">
        <div>
          <h3 className="text-sm font-extrabold text-slate-800">Add Expense</h3>
          {canSettle && (
            <p className="text-[11px] text-slate-500 mt-0.5">
              On behalf of driver — driver can report verbally (call/WhatsApp) and
              you key it in. Entries run the same rules check and approvals as
              driver-sent ones.
            </p>
          )}
        </div>

        {/* 1 — type chips */}
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
          {TYPES.map((t) => (
            <button
              key={t.code}
              type="button"
              aria-pressed={type === t.code}
              onClick={() => setType(t.code)}
              className={`flex flex-col items-center gap-1 rounded-2xl border p-3 transition-all duration-200 ${
                type === t.code
                  ? "border-brand-500 bg-brand-50 shadow-sm ring-1 ring-brand-200"
                  : "border-ink-200 bg-white hover:bg-ink-50"
              }`}
            >
              <span className="text-2xl leading-none" aria-hidden="true">{t.icon}</span>
              <span className={`text-[11px] font-bold ${type === t.code ? "text-brand-700" : "text-ink-600"}`}>
                {t.label}
              </span>
            </button>
          ))}
        </div>

        {/* 2 — amount (the only mandatory field) */}
        <div className="card p-4">
          <label htmlFor="ee-amount" className="label">Amount (₹)</label>
          <input
            id="ee-amount"
            type="number"
            inputMode="decimal"
            step="any"
            min="0"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0"
            autoFocus
            className="input text-center text-3xl font-extrabold tracking-tight"
          />
          {Number(amount) > 0 && (
            <p className="mt-2 text-center text-xs font-semibold text-brand-600">
              ₹
              {Number(amount).toLocaleString("en-IN", {
                maximumFractionDigits: 2,
              })}
            </p>
          )}
          {presets.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {presets.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setAmount(String(p))}
                  className="rounded-full border border-ink-200 bg-white px-3 py-1 text-xs font-bold text-ink-600 transition hover:bg-brand-50 hover:text-brand-700"
                >
                  ₹{p}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 3 — conditional fields for FUEL/DEF */}
        {needsFuelFields && (
          <div className="card p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="ee-liters" className="label">Liters</label>
                <input
                  id="ee-liters"
                  type="number"
                  step="0.1"
                  min="0"
                  value={liters}
                  onChange={(e) => setLiters(e.target.value)}
                  placeholder="0.0"
                  className="input"
                />
              </div>
              <div>
                <label htmlFor="ee-odo" className="label">Odometer (KM)</label>
                <input
                  id="ee-odo"
                  type="number"
                  step="any"
                  min="0"
                  value={odometer}
                  onChange={(e) => setOdometer(e.target.value)}
                  placeholder={trip?.current_odo ? String(trip.current_odo) : "0"}
                  className="input"
                />
              </div>
            </div>
            <div>
              <label htmlFor="ee-station" className="label">Pump / Station</label>
              <input
                id="ee-station"
                type="text"
                value={stationName}
                onChange={(e) => setStationName(e.target.value)}
                placeholder="e.g. Indian Oil, HP"
                className="input"
              />
            </div>
            <div>
              <label className="label">Fueling State</label>
              <div className="flex flex-wrap gap-2">
                {sortedStates.map((s) => (
                  <button
                    key={s.code}
                    type="button"
                    aria-pressed={stateCode === s.code}
                    onClick={() => setStateCode(s.code)}
                    className={`rounded-full border px-3 py-1 text-xs font-bold transition ${
                      stateCode === s.code
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-ink-200 bg-white text-ink-600 hover:bg-ink-50"
                    }`}
                  >
                    {s.is_favorite ? "★ " : ""}{s.code}
                  </button>
                ))}
                <select
                  aria-label="All states"
                  value={stateCode}
                  onChange={(e) => setStateCode(e.target.value)}
                  className="input h-8 w-auto py-0 text-xs"
                >
                  {states.map((s) => (
                    <option key={s.code} value={s.code}>{s.name}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Note field - shown for ALL expense types */}
        <div className="card p-4">
          <label className="label" htmlFor="ee-note">Note / विवरण (optional)</label>
          <input
            id="ee-note"
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. Pump name, location, purpose..."
            className="input"
          />
        </div>

        {/* Action buttons */}
        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            disabled={busy}
            onClick={() => save(true)}
            className="btn-primary flex-1 rounded-xl py-3 text-base disabled:opacity-50"
          >
            {busy ? "Saving…" : "💾 Save & Add Another"}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => save(false)}
            className="btn-secondary rounded-xl py-3 disabled:opacity-50"
          >
            Save & Finish
          </button>
        </div>
      </div>

      {/* Undo snackbar */}
      {savedExpense && (
        <div
          role="status"
          className="fixed inset-x-0 bottom-16 z-20 mx-auto flex w-max max-w-[92vw] items-center gap-3 rounded-xl border border-ink-200 bg-ink-900 px-4 py-2.5 text-sm text-white shadow-xl"
        >
          <span className="truncate">Saved {savedExpense.label}</span>
          <button
            type="button"
            onClick={undoLast}
            className="font-bold text-brand-300 underline-offset-2 hover:underline"
          >
            Undo
          </button>
        </div>
      )}

      <div className="table-wrap">
        <table className="table">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Type</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Amount</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Status</th>
              <th className="p-3 text-[10px] font-bold text-slate-500 uppercase">Odometer</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((e) => (
              <tr key={e.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="p-3 text-xs font-bold text-slate-800">
                  {e.exp_type}
                  {e.raw_receipt_text && (
                    <span className="block font-normal text-[10px] text-slate-500">
                      📝 {e.raw_receipt_text}
                    </span>
                  )}
                  {e.entry_source === "MANAGER_MANUAL" && (
                    <span className="block font-normal text-[10px] text-indigo-500">
                      ✍️ entered by manager
                    </span>
                  )}
                  {e.entry_source === "AUTO_POST" && (
                    <span className="block font-normal text-[10px] text-slate-400">
                      system
                    </span>
                  )}
                </td>
                <td className="p-3 text-xs text-slate-600">
                  ₹
                  {(Number(e.amount) || 0).toLocaleString("en-IN", {
                    maximumFractionDigits: 2,
                  })}
                </td>
                <td className="p-3 text-xs">
                  <span
                    className={`badge ${
                      e.manager_status === "APPROVED"
                        ? "bg-emerald-100 text-emerald-700"
                        : e.manager_status === "REJECTED"
                        ? "bg-rose-100 text-rose-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {e.manager_status}
                  </span>
                </td>
                <td className="p-3 text-xs text-slate-500">
                  {e.odometer != null && e.odometer !== ""
                    ? Number(e.odometer).toLocaleString("en-IN")
                    : "—"}
                </td>
              </tr>
            ))}
            {!expenses.length && (
              <tr>
                <td colSpan="4" className="p-6 text-center text-xs text-slate-400">
                  No expenses logged yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <LeaveGuardDialog blocker={blocker} onLeave={() => blocker.proceed()} />
    </div>
  );
}