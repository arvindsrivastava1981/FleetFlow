import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
} from "react";

const ToastContext = createContext(null);

let nextId = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timers = useRef({});

  const dismiss = useCallback((id) => {
    setToasts((list) => list.filter((t) => t.id !== id));
    const timer = timers.current[id];
    if (timer) {
      clearTimeout(timer);
      delete timers.current[id];
    }
  }, []);

  const push = useCallback(
    (type, message) => {
      const id = ++nextId;
      setToasts((list) => [...list, { id, type, message }]);
      // Keep the toast visible long enough to read, while still auto-dismissing.
      timers.current[id] = setTimeout(() => dismiss(id), 5000);
    },
    [dismiss]
  );

  const toast = useCallback(
    (message) => push("success", message),
    [push]
  );

  toast.success = useCallback((message) => push("success", message), [push]);
  toast.error = useCallback((message) => push("error", message), [push]);
  toast.info = useCallback((message) => push("info", message), [push]);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      {/* Toast stack — fixed top-right, above the sticky header (z-30). */}
      <div
        aria-live="polite"
        className="pointer-events-none fixed right-4 top-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={`pointer-events-auto flex items-start justify-between gap-3 rounded-xl border px-4 py-3 text-sm shadow-cardHover animate-[toast-in_0.2s_ease-out] ${
              t.type === "error"
                ? "alert-error"
                : t.type === "info"
                ? "alert-info"
                : "alert-success"
            }`}
          >
            <span className="min-w-0 flex-1">{t.message}</span>
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border border-current/[0.15] text-xs font-bold leading-none opacity-70 transition hover:bg-black/5 hover:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-current/40"
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a <ToastProvider>");
  }
  return ctx;
}
