import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../lib/api.js", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    postForm: vi.fn(),
  },
  getToken: vi.fn(() => null),
  setToken: vi.fn(),
}));

import { api, setToken } from "../lib/api.js";
import { AuthProvider, useAuth } from "../context/AuthContext.jsx";

const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>;

describe("AuthContext (audit E-4)", () => {
  afterEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("login stores the token + user via setToken/setUser", async () => {
    api.postForm.mockResolvedValue({
      token: "tok-1",
      user: { id: 7, username: "ravi", role: "trip_manager" },
      landing: "/dashboard",
    });
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      const landing = await result.current.login("ravi", "pw");
      expect(landing).toBe("/dashboard");
    });

    expect(result.current.user).toEqual({
      id: 7,
      username: "ravi",
      role: "trip_manager",
    });
    expect(setToken).toHaveBeenCalledWith("tok-1");
  });

  it("login throws a readable error when no token is returned", async () => {
    api.postForm.mockResolvedValue(null);
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await expect(result.current.login("x", "y")).rejects.toThrow("Login failed");
    });
    expect(setToken).not.toHaveBeenCalledWith(expect.anything());
  });

  it("logout clears the local session state", async () => {
    api.postForm.mockResolvedValue({ token: "t", user: { id: 1 }, landing: "/dashboard" });
    api.post.mockResolvedValue({ logged_out: true });
    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.login("u", "p");
    });
    expect(result.current.user).not.toBeNull();

    await act(async () => {
      await result.current.logout();
    });
    expect(result.current.user).toBeNull();
    expect(setToken).toHaveBeenCalledWith(null);
  });

  it("boot resolves loading and captures expires_at from /me", async () => {
    api.get.mockResolvedValue({
      user: { id: 2, username: "owner", role: "super_admin" },
      expires_at: 1900000000,
    });
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.user.username).toBe("owner");
    expect(result.current.expiresAt).toBe(1900000000);
  });

  it("refreshSession tracks the new sliding expiry (audit E-10)", async () => {
    api.get.mockResolvedValue({
      user: { id: 2, username: "owner", role: "super_admin" },
      expires_at: 100,
    });
    api.post.mockResolvedValue({ expires_at: 200 });
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      const next = await result.current.refreshSession();
      expect(next).toBe(200);
    });
    expect(api.post).toHaveBeenCalledWith("/api/v1/auth/refresh");
    expect(result.current.expiresAt).toBe(200);
  });
});
