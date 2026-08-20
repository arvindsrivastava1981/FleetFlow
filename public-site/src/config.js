// Public marketing site config.
//
// VITE_APP_URL is the absolute origin of the app SPA (e.g.
// https://app.fleetflow.app). Every "Log in" link on the marketing site
// points there. Defaults to "/" so links still resolve to this site in local
// dev / before the app domain is configured on Render.
const APP_URL = (import.meta.env.VITE_APP_URL || "").replace(/\/+$/, "");

export function app(path) {
  return `${APP_URL}${path}`;
}