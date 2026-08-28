// Public marketing site config.
//
// The app SPA lives at a separate origin (the Render Static Site
// "vahankhata-app"). Every "Log in" link on the marketing site points there.
const APP_URL = (import.meta.env.VITE_APP_URL || "").replace(/\/+$/, "");
const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

export function app(path) {
  return `${APP_URL}${path}`;
}

// Build a full URL for an `/api/v1/*` endpoint.
// Dev (VITE_API_URL=""):    relative path → Vite dev proxy → localhost backend
// Prod (VITE_API_URL=https://api.vahankhata.in): absolute cross-origin URL
export function api(path) {
  return `${API_URL}${path}`;
}