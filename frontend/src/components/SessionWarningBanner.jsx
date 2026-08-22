import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";

const WARN_BEFORE_MIN = 15;

// Audit E-10: amber banner when the session is within its warning window,
// with a one-click sliding renewal ("Stay signed in") and a dismiss option
// (suppressed for 10 minutes after dismissing).
export default function SessionWarningBanner() {
  const { user, expiresAt, refreshSession } = useAuth();
  const [remainingMin, setRemainingMin] = useState(null);
  const dismissedUntil = useRef(0);

  useEffect(() => {
    if (!user || !expiresAt) {
      setRemainingMin(null);
      return undefined;
    }
    function tick() {
      setRemainingMin(Math.round((expiresAt * 1000 - Date.now()) / 60000));
    }
    tick();
    const iv = setInterval(tick, 30_000);
    return () => clearInterval(iv);
  }, [user, expiresAt]);

  if (!user || remainingMin === null || remainingMin > WARN_BEFORE_MIN || remainingMin < 0) {
    return null;
  }
  if (Date.now() < dismissedUntil.current) return null;

  return (
    <div className="flex flex-wrap items-center justify-center gap-3 bg-amber-100 px-4 py-2 text-xs font-semibold text-amber-900">
      <span>⏳ Your session ends in about {remainingMin} min — save your work.</span>
      <button
        type="button"
        onClick={() => refreshSession().catch(() => {})}
        className="rounded-full bg-amber-600 px-3 py-1 font-bold text-white transition hover:bg-amber-700"
      >
        Stay signed in
      </button>
      <button
        type="button"
        onClick={() => {
          dismissedUntil.current = Date.now() + 10 * 60 * 1000;
          setRemainingMin(null);
        }}
        className="underline"
      >
        Dismiss
      </button>
    </div>
  );
}
