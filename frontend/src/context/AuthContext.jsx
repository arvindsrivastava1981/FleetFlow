import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { api, getToken, setToken } from "../lib/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [expiresAt, setExpiresAt] = useState(null); // audit E-10 (epoch s)
  const [loading, setLoading] = useState(true);

  // On boot, validate the stored token via /me. This runs on EVERY route,
  // including the login page ("/"). On 401 api.js redirects to the login page
  // unless the app is already there; here we just resolve whether a session
  // exists so ProtectedRoute can gate authed routes.
  useEffect(() => {
    (async () => {
      try {
        const data = await api.get("/api/v1/auth/me");
        setUser(data.user);
        setExpiresAt(data.expires_at ?? null);
      } catch {
        setToken(null);
        setUser(null);
        setExpiresAt(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (username, password) => {
    const data = await api.postForm("/api/v1/auth/login", { username, password });
    // postForm resolves to null on empty bodies; guard so a missing response
    // fails loudly with a readable message instead of a JSON parse error.
    if (!data || !data.token) throw new Error("Login failed");
    setToken(data.token);
    setUser(data.user);
    // Normalize the server-provided landing to a React SPA route. The backend
    // returns the legacy HTML paths (/admin, /manager, /driver) which are NOT part
    // of the React app and would either hit a dead SPA route or a full page-load to
    // the server-rendered pages (and previously hard-redirected away). Every role
    // lands on the SPA dashboard instead.
    return "/dashboard";
  }, []);

  // Social login: the credential has already been verified by the backend
  // (POST /auth/google | /auth/facebook); this just adopts the session.
  const loginWithSocial = useCallback(async (path, payload) => {
    const data = await api.post(path, payload);
    if (!data || !data.token) throw new Error("Social login failed");
    setToken(data.token);
    setUser(data.user);
    return "/dashboard";
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/api/v1/auth/logout");
    } catch {
      // best-effort; clear local token regardless
    }
    setToken(null);
    setUser(null);
    setExpiresAt(null);
  }, []);

  // Audit E-10: sliding renewal — extend the session and track the new expiry.
  const refreshSession = useCallback(async () => {
    const data = await api.post("/api/v1/auth/refresh");
    if (data?.expires_at) setExpiresAt(data.expires_at);
    return data?.expires_at ?? null;
  }, []);

  const value = { user, setUser, loading, login, loginWithSocial, logout, expiresAt, refreshSession };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}