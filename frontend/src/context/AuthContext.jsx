import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { api, getToken, setToken } from "../lib/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On boot, validate the stored token (or a server cookie) via /me.
  useEffect(() => {
    (async () => {
      try {
        const data = await api.get("/api/v1/auth/me");
        setUser(data.user);
      } catch {
        setToken(null);
        setUser(null);
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
    return data.landing || "/dashboard";
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch("/logout");
    } catch {
      // best-effort; ignore
    }
    setToken(null);
    setUser(null);
  }, []);

  const value = { user, setUser, loading, login, logout };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}