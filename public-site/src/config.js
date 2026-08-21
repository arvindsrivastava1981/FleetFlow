// Public marketing site config.
//
// The app SPA lives at a separate origin (the Render Static Site
// "vahankhata-app"). Every "Log in" link on the marketing site points there.
const APP_URL = (import.meta.env.VITE_APP_URL || "/APP_URL").replace(/\/+$/, "");

export function app(path) {
  return `${APP_URL}${path}`;
}