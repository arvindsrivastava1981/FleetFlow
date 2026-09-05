import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import Loader from "../components/Loader.jsx";
import ShortcutBar from "../components/ShortcutBar.jsx";
import useUnsavedGuard, { LeaveGuardDialog } from "../hooks/useUnsavedGuard.jsx";

const EXPENSE_TYPES = [
  "FUEL", "DEF", "TOLL", "REPAIR", "CHALLAN", "MISC", "GOODS_BUY", "GOODS_SALE",
  "CASH_ADVANCE", "DRIVER_SALARY",
];

export default function TripDetailPage() {
  const { tripCode } = useParams();
  const { user } = useAuth();
  const toast = useToast();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [expType, setExpType] = useState("FUEL");
  const [amount, setAmount] = useState("");
  const [liters, setLiters] = useState("");
  const [rate, setRate] = useState("");
  const [odometer, setOdometer] = useState("");
  const [busy, setBusy] = useState(false);
  const [settleBusy, setSettleBusy] = useState(false);
  const [endOdo, setEndOdo] = useState("");
  const skipRef = useRef(false);
  const dirty = Boolean(amount || liters || rate || odometer);
  const blocker = useUnsavedGuard(dirty, skipRef);

  function load() {
    setError("");
    api
      .get(`/api/v1/trips/${tripCode}`)
      .then(setData)
      .catch((e) => setError(e.message));
  }

  useEffect(load, [tripCode]);

  // Keyboard data-entry shortcut: digit 1-9, 0 (no field focused) switches the
  // expense type by position — mirrors the quick-entry screen.
  useEffect(() => {
    function onKey(e) {
      const el = e.target;
      const isControl =
        el &&
        (el.tagName === "INPUT" ||
          el.tagName === "SELECT" ||
          el.tagName === "TEXTAREA" ||
          el.tagName === "BUTTON");
      if (isControl || !/^[0-9]$/.test(e.key)) return;
      const idx = e.key === "0" ? EXPENSE_TYPES.length - 1 : Number(e.key) - 1;
      if (idx >= 0 && idx < EXPENSE_TYPES.length) {
        e.preventDefault();
        setExpType(EXPENSE_TYPES[idx]);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function addExpense(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/api/v1/expenses", {
        trip_code: tripCode,
        exp_type: expType,
        amount: Number(amount),
        liters: Number(liters || 0),
        rate: Number(rate || 0),
        odometer: Number(odometer || 0),
      });
      setAmount("");
      setLiters("");
      setRate("");
      setOdometer("");
      toast.success("Expense logged.");
      load();
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function settleTrip() {
    setSettleBusy(true);
    setError("");
    try {
      await api.post(`/api/v1/trips/${tripCode}/settle`, {
        end_odo: Number(endOdo),
      });
      setEndOdo("");
      toast.success("Trip settled.");
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
                value={endOdo}
                onChange={(e) => setEndOdo(e.target.value)}
                placeholder={`Min: ${trip?.start_odo ?? 0}`}
                className="input text-sm w-full"
                required
              />
            </div>
            <button
              onClick={settleTrip}
              disabled={settleBusy || !endOdo}
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

      <div className="card-pad">
        <h3 className="text-sm font-extrabold text-slate-800 mb-1">Log Expense</h3>
        {canSettle && (
          <p className="text-[11px] text-slate-500 mb-3">
            On behalf of driver — driver can report verbally (call/WhatsApp) and
            you key it in. Entries run the same rules check and approvals as
            driver-sent ones.{" "}
            <a
              href={`/trips/${tripCode}/log`}
              className="font-bold text-brand-700 underline"
            >
              ⚡ Use quick entry
            </a>
          </p>
        )}
        <form onSubmit={addExpense} className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <select
            value={expType}
            onChange={(e) => setExpType(e.target.value)}
            className="input text-sm"
            required
          >
            {EXPENSE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <input
            type="number"
            step="any"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Amount ₹"
            required
            autoFocus
            className="input text-sm"
          />
          <input
            type="number"
            step="0.1"
            value={liters}
            onChange={(e) => setLiters(e.target.value)}
            placeholder="Liters"
            className="input text-sm"
          />
          <input
            type="number"
            step="0.1"
            value={rate}
            onChange={(e) => setRate(e.target.value)}
            placeholder="Rate ₹/L"
            className="input text-sm"
          />
          <input
            type="number"
            step="any"
            value={odometer}
            onChange={(e) => setOdometer(e.target.value)}
            placeholder="Odometer (KM)"
            className="input text-sm col-span-2"
          />
          <button
            type="submit"
            disabled={busy}
            className="col-span-2 btn-primary py-2 rounded-xl transition shadow disabled:opacity-50"
          >
            {busy ? "Saving…" : "Log Expense"}
          </button>
          {Number(amount) > 0 && (
            <p className="col-span-2 md:col-span-4 -mt-1 text-right text-xs font-semibold text-brand-600">
              Amount: ₹
              {Number(amount).toLocaleString("en-IN", {
                maximumFractionDigits: 2,
              })}
            </p>
          )}
        </form>
      </div>

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
                  {e.exp_type === "MISC" && e.raw_receipt_text && (
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

      <ShortcutBar
        items={[
          { keys: ["1–9", "0"], label: "pick type (no field focused)" },
          { keys: ["Enter"], label: "log expense" },
        ]}
      />
      <LeaveGuardDialog blocker={blocker} onLeave={() => blocker.proceed()} />
    </div>
  );
}