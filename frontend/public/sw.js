// VahanKhata service worker — offline app shell + runtime caching.
//
// Static assets (same-origin, hashed filenames) are cached-first; navigation
// serves the cached shell so the SPA boots offline; `/api/*` is network-only so
// stale financial data is never served offline.
const CACHE = "vk-shell-v1";
const SHELL = ["/", "/index.html", "/manifest.webmanifest", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);
  // API is never cached — always go to the network.
  if (url.pathname.startsWith("/api/")) return;
  if (url.origin !== self.location.origin) return;

  // App-shell navigation: serve the cached shell first (SPA fallback).
  if (event.request.mode === "navigate") {
    event.respondWith(
      caches.match("/").then(
        (hit) =>
          hit ||
          fetch(event.request).then((res) => {
            const clone = res.clone();
            caches.open(CACHE).then((cache) => cache.put("/", clone));
            return res;
          }),
      ),
    );
    return;
  }

  // Static assets: cache-first, populate the cache in the background.
  event.respondWith(
    caches.match(event.request).then((hit) => {
      if (hit) return hit;
      return fetch(event.request).then((res) => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then((cache) => cache.put(event.request, clone));
        }
        return res;
      });
    }),
  );
});
