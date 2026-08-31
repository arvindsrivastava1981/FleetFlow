import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";

// In-app notification bell (feature F-3): computed alert feed fetched from
// GET /api/v1/notifications. Nothing is persisted server-side; the badge
// count is simply the number of derived items.
export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const ref = useRef(null);

  function load() {
    api.get("/api/v1/notifications").then(setItems).catch(() => {});
  }

  useEffect(() => {
    load();
    // Poll for new alerts every 60s so the badge stays fresh without a
    // manual click; also refresh when the tab regains focus.
    const interval = setInterval(load, 60_000);
    function onFocus() {
      if (document.visibilityState === "visible") load();
    }
    document.addEventListener("visibilitychange", onFocus);
    function onDoc(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onFocus);
      document.removeEventListener("mousedown", onDoc);
    };
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => {
          const next = !open;
          setOpen(next);
          if (next) load();
        }}
        aria-label="Notifications"
        className="relative flex h-9 w-9 items-center justify-center rounded-full border border-ink-200 bg-white text-base shadow-sm transition hover:bg-ink-50"
      >
        🔔
        {items.length > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-rose-600 px-1 text-[9px] font-bold text-white">
            {items.length}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 rounded-xl border border-ink-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-ink-100 px-4 py-2.5">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-500">
              Notifications
            </span>
            <button
              type="button"
              onClick={load}
              className="text-[10px] font-semibold text-brand-600 underline"
            >
              refresh
            </button>
          </div>
          <div className="max-h-80 overflow-y-auto p-2">
            {items.length === 0 && (
              <p className="px-2 py-6 text-center text-xs text-ink-400">
                You're all caught up 🎉
              </p>
            )}
            {items.map((n, i) => (
              <div key={`${n.type}-${i}`} className="rounded-lg px-3 py-2 hover:bg-ink-50">
                <p className="text-xs font-bold text-ink-800">{n.title}</p>
                <p className="mt-0.5 text-[11px] leading-snug text-ink-500">{n.detail}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
