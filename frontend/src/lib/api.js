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
// The SPA is served same-origin by the FastAPI backend (frontend/dist is mounted
// at "/" on the same Render container), and the must always be relative so
// every request hits the backend that issued the session / token. A hardcoded
// absolute fallback (e.g. http://localhost:8000) would send auth'd calls to the
// wrong origin in production and trigger 401 "unauthorized".
//
// VITE_API_BASE_URL is supported strictly for local cross-origin dev; production
// builds must NOT set it so relative paths are used (see vite.config.js proxy).
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

  // Expired / invalid session: clear the local token and bounce to /login. We
  // skip the login endpoint itself (a wrong-password 401 must NOT redirect the
  // page) and skip while already on /login to avoid a redirect loop.
  if (res.status === 401 && !path.includes("/auth/login")) {
    if (getToken()) setToken(null);
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
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

  // Same expired-session handling as `request()` — clear token and bounce to
  // /login unless the call was the login attempt itself.
  if (res.status === 401 && !path.includes("/auth/login")) {
    if (getToken()) setToken(null);
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
  }

  return parseResponse(res);
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  del: (path) => request(path, { method: "DELETE" }),
  postForm,
};