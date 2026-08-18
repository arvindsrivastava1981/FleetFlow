// Lightweight fetch wrapper for the /api/v1 JSON API.
// - Attaches `Authorization: Bearer <token>` from localStorage when present.
// - Returns the parsed JSON body; throws on non-2xx with a decoded error message.
// - Uses relative paths so the SPA is fully portable across single-origin deploys.

const TOKEN_KEY = "vk_token";

// Base URL for the /api/v1 JSON API. Reads VITE_API_BASE_URL at build time so the
// hosted SPA can target the Render backend; falls back to localhost for local dev.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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

  // Empty (204) responses
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

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  del: (path) => request(path, { method: "DELETE" }),
};