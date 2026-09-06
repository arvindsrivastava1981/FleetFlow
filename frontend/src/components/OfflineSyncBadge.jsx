import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { drain, pendingCount } from "../lib/offlineQueue.js";
import { useToast } from "../context/ToastContext.jsx";

// Syncs queued offline receipts on boot + reconnect, and shows a badge while
// any are still pending. Rendered once in the app shell (Layout header).
export default function OfflineSyncBadge() {
  const toast = useToast();
  const [pending, setPending] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function sync() {
      const { synced } = await drain((payload) =>
        api.post("/api/v1/expenses", payload),
      );
      if (cancelled) return;
      setPending(await pendingCount());
      if (synced > 0) {
        toast.success(`Synced ${synced} offline expense${synced > 1 ? "s" : ""}.`);
      }
    }

    sync();
    window.addEventListener("online", sync);
    return () => {
      cancelled = true;
      window.removeEventListener("online", sync);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!pending) return null;
  return (
    <span
      className="badge badge-warning"
      title={`${pending} expense${pending > 1 ? "s" : ""} saved offline — will sync when online`}
    >
      ⏳ {pending}
    </span>
  );
}
