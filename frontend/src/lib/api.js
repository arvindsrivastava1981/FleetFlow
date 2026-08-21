// Parse a fetch Response into its JSON payload. A body is optional: 204 and
// other empty responses resolve to `null` instead of throwing
// "Unexpected end of JSON input" when callers `.json()` an empty body.
async function parseResponse(res) {
  if (res.status === 204) return null;
  let payload = null;
  try {
    payload = await res.json();
  } catch {
    payload = null;
  }
  if (!res.ok) {
    const message = payload?.error || `Request failed (${res.status})`;
    throw new ApiError(message, res.status, payload?.code);
  }
  return payload?.data !== undefined ? payload.data : payload;
}

const TOKEN_KEY = "vk_token";

// Base URL for the /api/v1 JSON API.
//
// Defaults to same-origin (""). Keep this so local `npm run dev` (which proxies
// /api to the FastAPI backend) and the single-container Docker deploy both work.
//
// For the two-service Render setup (static SPA on vahankhata-app + API on
// vahankhata-api), render.yaml sets VITE_API_BASE_URL=https://api.vahankhata.in
// at build time so the static bundle calls the API cross-origin; the API's CORS
// allowlist (backend/app/main.py) includes that SPA origin. Never hardcode a
// local fallback here (e.g. http://localhost:8000) — it would break production.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export class UnauthorizedError extends ApiError {
  constructor() {
    super("Unauthorized", 401, "UNAUTHORIZED");
  }
}

// Centralized 401 handling: drop the dead session token and bounce the user
// back to the login page ("/"). The redirect is skipped when the app is
// already on "/" so anonymous visitors and the boot-time /auth/me probe never
// loop, and failed logins simply stay on the form.
function handleUnauthorized() {
  if (window.location.pathname !== "/") {
    window.location.replace("/");
  }
}

async function request(path, { method = "GET", body } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // On 401 (expired / invalid session): clear the local token so subsequent
  // calls don't keep sending a dead token, redirect to the login page ("/"),
  // and surface an UnauthorizedError for callers that want to react too.
  if (res.status === 401 && !path.includes("/auth/login")) {
    setToken(null);
    handleUnauthorized();
    throw new UnauthorizedError();
  }

  return parseResponse(res);
}

// Form-encoded POST (e.g. /api/v1/auth/login), so responses go through the same
// safe parsing/error handling as JSON calls instead of a brittle `res.json()`.
async function postForm(path, form) {
  const headers = { "Content-Type": "application/x-www-form-urlencoded" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    method: "POST",
    headers,
    body: new URLSearchParams(form).toString(),
  });

  // On 401 (expired / invalid session): clear the local token and redirect
  // to the login page ("/"), same as JSON requests.
  if (res.status === 401 && !path.includes("/auth/login")) {
    setToken(null);
    handleUnauthorized();
    throw new UnauthorizedError();
  }

  return parseResponse(res);
}

async function requestBlob(path) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, { method: "GET", headers });

  // On 401 (expired / invalid session): clear the local token and redirect
  // to the login page ("/"), same as JSON requests. Throw the typed
  // UnauthorizedError so callers can distinguish it like other API calls.
  if (res.status === 401) {
    setToken(null);
    handleUnauthorized();
    throw new UnauthorizedError();
  }
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const payload = await res.json();
      if (payload?.error) message = payload.error;
    } catch {
      // non-JSON error body; fall back to the generic message
    }
    throw new ApiError(message, res.status);
  }
  return res.blob();
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  del: (path) => request(path, { method: "DELETE" }),
  postForm,
  blob: requestBlob,
};