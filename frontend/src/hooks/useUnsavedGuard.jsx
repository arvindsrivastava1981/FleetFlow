import { useEffect, useRef } from "react";
import { useBlocker } from "react-router-dom";

// Guards data-entry screens against unintentional data loss.
//  - `beforeunload`: native prompt when the tab is closed / refreshed.
//  - `useBlocker`: intercepts in-app <Link>/useNavigate navigation.
// Pass a mutable `skipRef` and set `skipRef.current = true` BEFORE a deliberate
// programmatic navigate (e.g. right after a successful save) so navigation is
// never blocked in that flow.
export default function useUnsavedGuard(dirty, skipRef) {
  const localSkipRef = useRef(false);
  const activeSkipRef = skipRef || localSkipRef;

  // Native browser guard (tab close / refresh / external navigation).
  useEffect(() => {
    if (!dirty) return undefined;
    const onBeforeUnload = (e) => {
      if (activeSkipRef.current) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty, activeSkipRef]);

  // In-app (SPA) navigation guard.
  const blocker = useBlocker(
    dirty
      ? ({ currentLocation, nextLocation }) =>
          !activeSkipRef.current &&
          currentLocation.pathname !== nextLocation.pathname
      : false,
  );
  return blocker;
}

// Confirm dialog shown when an unsaved navigation is blocked.
export function LeaveGuardDialog({ blocker, onLeave }) {
  if (!blocker || blocker.state !== "blocked") return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/50 p-4"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="unsaved-title"
    >
      <div className="w-full max-w-sm rounded-2xl border border-ink-200 bg-white p-5 shadow-xl">
        <h3 id="unsaved-title" className="text-sm font-extrabold text-ink-900">
          You have unsaved changes
        </h3>
        <p className="mt-1 text-xs text-ink-500">
          Leave this page? Your unsaved entry will be lost.
        </p>
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={() => blocker.reset()}
            autoFocus
            className="btn-primary flex-1"
          >
            Keep editing
          </button>
          <button
            type="button"
            onClick={onLeave}
            className="btn-secondary flex-1"
          >
            Discard &amp; leave
          </button>
        </div>
      </div>
    </div>
  );
}