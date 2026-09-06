import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api.js";
import { useToast } from "../context/ToastContext.jsx";
import { useShortcuts } from "../context/ShortcutContext.jsx";
import Loader from "../components/Loader.jsx";
import useUnsavedGuard, { LeaveGuardDialog } from "../hooks/useUnsavedGuard.jsx";

// Phase-1 tap-first expense entry: icon-chip type picker, one big amount,
// conditional fields only. 2 taps + 1 number for most entries.

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

export default function ExpenseEntryPage() {
  const { tripCode } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { setShortcuts } = useShortcuts();
  const [trip, setTrip] = useState(null);
  const [states, setStates] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [type, setType] = useState("FUEL");
  const [amount, setAmount] = useState("");
  const [liters, setLiters] = useState("");
  const [odometer, setOdometer] = useState("");
  const [stateCode, setStateCode] = useState("");
  const [note, setNote] = useState("");
  const [stationName, setStationName] = useState("");
  const [settleOdo, setSettleOdo] = useState("");
  const [settleBusy, setSettleBusy] = useState(false);
  const [savedExpense, setSavedExpense] = useState(null); // {id, label} for Undo
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
    } catch (err) {
      toast.error(err.message);
      setSavedExpense(null);
    }
  }

  useEffect(() => {
    api
      .get(`/api/v1/trips/${tripCode}`)
      .then((d) => {
        const t = d?.trip || d;
        setTrip(t);
        setOdometer(t?.current_odo ? String(t.current_odo) : "");
        setStateCode(t?.state_code || "UP");
        setSettleOdo(t?.current_odo ? String(t.current_odo) : "");
      })
      .catch((e) => setError(e.message));
    api
      .get("/api/v1/states?source=benchmarks")
      .then((d) => setStates(d?.states || d || []))
      .catch(() => {});
  }, [tripCode]);

  const presets = useMemo(() => loadPresets()[type] || [], [type, amount]);
  const isFuel = FUELISH.has(type);
  const needsNote = type === "MISC";
  const autoRate =
    isFuel && Number(liters) > 0 && Number(amount) > 0
      ? (Number(amount) / Number(liters)).toFixed(2)
      : null;

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
      const isControl = el && (el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA" || el.tagName === "BUTTON");
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
        liters: isFuel ? Number(liters || 0) : 0,
        odometer: Number(odometer || 0),
        ...(isFuel && stateCode ? { state_code: stateCode } : {}),
        ...(isFuel && stationName.trim() ? { station_name: stationName.trim() } : {}),
        ...(needsNote && note.trim() ? { raw_receipt_text: note.trim() } : {}),
      });
      rememberAmount(type, Number(amount));
      if (res?.expense_id) {
        setSavedExpense({ id: res.expense_id, label: `${type} ₹${amount}` });
      }
      toast.success(`${type} ₹${amount} saved.`);
      if (again) {
        setAmount("");
        setNote("");
        setLiters("");
        document.getElementById("ee-amount")?.focus();
      } else {
        skipRef.current = true;
        navigate(`/trips/${tripCode}`);
      }
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function settle() {
    const endOdo = Number(settleOdo || 0);
    const startOdo = Number(trip?.start_odo);
    if (startOdo && endOdo && endOdo < startOdo) {
      toast.error(
        `End odometer (${endOdo}) is below the trip start (${startOdo}) — check it.`,
      );
      return;
    }
    setSettleBusy(true);
    try {
      await api.post(`/api/v1/trips/${tripCode}/settle`, {
        end_odo: endOdo,
      });
      toast.success("Trip settled. 🤝");
      skipRef.current = true;
      navigate(`/trips/${tripCode}`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSettleBusy(false);
    }
  }

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!trip) return <Loader label="Loading trip…" />;
  return (
    <div className="mx-auto max-w-xl space-y-5">
      <div>
        <h2 className="page-title">Add Expense</h2>
        <p className="page-sub">
          {tripCode} · {trip.vehicle_no} · {trip.driver_name || "—"}
        </p>
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
                ₹{p.toLocaleString("en-IN")}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 3 — conditional fields only */}
      {isFuel && (
        <div className="card grid grid-cols-2 gap-3 p-4">
          <div>
            <label className="label" htmlFor="ee-liters">Litres (optional)</label>
            <input
              id="ee-liters"
              type="number"
              inputMode="decimal"
              step="any"
              min="0"
              value={liters}
              onChange={(e) => setLiters(e.target.value)}
              placeholder="0"
              className="input"
            />
          </div>
          <div>
            <label className="label" htmlFor="ee-odo">Odometer</label>
            <input
              id="ee-odo"
              type="number"
              inputMode="decimal"
              step="any"
              min="0"
              value={odometer}
              onChange={(e) => setOdometer(e.target.value)}
              className="input"
            />
          </div>
          {autoRate && (
            <p className="col-span-2 text-[11px] font-semibold text-brand-700">
              ≈ ₹{autoRate}/L (auto)
            </p>
          )}
          <div className="col-span-2">
            <label className="label" htmlFor="ee-station">Pump / Station (optional)</label>
            <input
              id="ee-station"
              type="text"
              value={stationName}
              onChange={(e) => setStationName(e.target.value)}
              placeholder="e.g. HP Pump, Bareilly Road"
              className="input"
            />
          </div>
          <div className="col-span-2">
            <p className="label">Fueling State</p>
            <div className="flex flex-wrap gap-2">
              {states.slice(0, 8).map((s) => (
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

      <div className="flex flex-col gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => save(true)}
          className="btn-primary rounded-xl py-3 text-base disabled:opacity-50"
        >
          {busy ? "Saving…" : "💾 Save & Add Another"}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => save(false)}
          className="btn-secondary rounded-xl py-2.5 disabled:opacity-50"
        >
          Save & Finish
        </button>
      </div>
      {/* 4 — one-tap close (ACTIVE trips only) */}
      {trip.status === "ACTIVE" && (
        <div className="card p-4">
          <p className="label">Finish Trip</p>
          <div className="mt-2 flex items-end gap-3">
            <div className="flex-1">
              <label className="label" htmlFor="ee-endodo">End Odometer</label>
              <input
                id="ee-endodo"
                type="number"
                inputMode="decimal"
                step="any"
                min="0"
                value={settleOdo}
                onChange={(e) => setSettleOdo(e.target.value)}
                className="input"
              />
            </div>
            <button
              type="button"
              disabled={settleBusy}
              onClick={settle}
              className="btn-success rounded-xl px-5 py-3 disabled:opacity-50"
            >
              {settleBusy ? "Settling…" : "🤝 Settle Trip"}
            </button>
          </div>
          <p className="mt-2 text-[11px] text-slate-500">
            Fails while expenses are still pending approval — approve them first
            (Expense Approvals).
          </p>
        </div>
      )}

      <LeaveGuardDialog blocker={blocker} onLeave={() => blocker.proceed()} />
    </div>
  );
}
