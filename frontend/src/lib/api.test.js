import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, getToken, setToken } from "./api.js";

function mockFetch(status, body) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

describe("api request layer (audit E-4)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("unwraps the data envelope on success", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { data: { hello: "world" } }));
    await expect(api.get("/api/v1/x")).resolves.toEqual({ hello: "world" });
  });

  it("resolves null for an empty 204 body", async () => {
    vi.stubGlobal("fetch", mockFetch(204, null));
    await expect(api.del("/api/v1/x")).resolves.toBeNull();
  });

  it("throws ApiError carrying the server message + code", async () => {
    vi.stubGlobal("fetch", mockFetch(400, { error: "bad thing", code: "BAD" }));
    const promise = api.post("/api/v1/x", {});
    await expect(promise).rejects.toBeInstanceOf(ApiError);
    await promise.catch((e) => {
      expect(e.message).toBe("bad thing");
      expect(e.code).toBe("BAD");
      expect(e.status).toBe(400);
    });
  });

  it("clears the stored token and raises UnauthorizedError on 401", async () => {
    setToken("stale-token");
    // Default jsdom location is http://localhost/ → pathname "/" so the
    // redirect-to-login side effect is skipped and stays assert-free.
    vi.stubGlobal("fetch", mockFetch(401, { error: "expired" }));
    const promise = api.get("/api/v1/secure");
    await expect(promise).rejects.toBeInstanceOf(ApiError);
    expect(getToken()).toBeNull();
  });
});
