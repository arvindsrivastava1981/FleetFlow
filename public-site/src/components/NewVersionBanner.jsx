import { useEffect, useState } from "react";

/**
 * New-version rollout banner (public marketing site).
 *
 * Every deploy produces a new hashed entry bundle (`/assets/index-<hash>.js`).
 * This component periodically re-fetches `index.html` from the server with
 * `cache: "no-store"` and compares the entry bundle filename against the one
 * this page was booted with. When they differ, a new version has been deployed
 * and a fixed top banner offers a one-click "Reload App" which clears stale
 * Cache Storage entries and hard-reloads — visitors never need to manually
 * clear their browser cache to see new changes.
 */
function getCurrentEntryScript() {
  const script = document.querySelector('script[src*="/assets/"]');
  if (!script) return null; // dev server / inline scripts — skip detection
  const match = script.src.match(/assets\/[^/]+\.js/);
  return match ? match[0] : null;
}

async function fetchLatestEntryScript() {
  try {
    const res = await fetch(`/?_v=${Date.now()}`, {
      cache: "no-store",
      headers: { Accept: "text/html" },
    });
    if (!res.ok) return null;
    const html = await res.text();
    const match = html.match(/assets\/[^"']+\.js/);
    return match ? match[0] : null;
  } catch {
    return null; // offline / network error — silently ignore
  }
}

async function clearStaleCaches() {
  if (typeof caches === "undefined") return;
  try {
    const keys = await caches.keys();
    await Promise.all(keys.map((key) => caches.delete(key)));
  } catch {
    /* best-effort */
  }
}

export default function NewVersionBanner() {
  const [newVersion, setNewVersion] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const current = getCurrentEntryScript();
    if (!current) return undefined;

    const check = async () => {
      const latest = await fetchLatestEntryScript();
      if (!cancelled && latest && latest !== current) setNewVersion(true);
    };

    check();
    const interval = setInterval(check, 60_000);
    // Re-check immediately when the user returns to the tab.
    const onVisible = () => {
      if (document.visibilityState === "visible") check();
    };
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", check);
    return () => {
      cancelled = true;
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", check);
    };
  }, []);

  if (!newVersion) return null;

  const reload = async () => {
    await clearStaleCaches();
    window.location.reload();
  };

  return (
    <div
      role="alert"
      className="fixed inset-x-0 top-0 z-[100] flex flex-col items-center justify-between gap-2 bg-brand-600 px-4 py-2 text-white shadow-lg transition-all duration-200 sm:flex-row"
    >
      <p className="text-sm font-medium">
        🎉 A new version is available — reload to get the latest updates.
      </p>
      <button
        type="button"
        onClick={reload}
        aria-label="Reload site to load the new version"
        className="w-full rounded-md bg-white px-4 py-1.5 text-sm font-semibold text-brand-700 transition-all duration-200 hover:bg-brand-50 sm:w-auto"
      >
        Reload App
      </button>
    </div>
  );
}
