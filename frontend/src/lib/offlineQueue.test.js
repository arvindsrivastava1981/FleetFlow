import "fake-indexeddb/auto";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  drain,
  enqueue,
  isNetworkError,
  loadQueue,
  pendingCount,
} from "./offlineQueue.js";

const DB_NAME = "vk_offline_queue";

async function resetDb() {
  if (!globalThis.indexedDB) return;
  await new Promise((resolve) => {
    const req = indexedDB.deleteDatabase(DB_NAME);
    req.onsuccess = resolve;
    req.onerror = resolve;
    req.onblocked = resolve;
  });
}

describe("offlineQueue", () => {
  afterEach(resetDb);

  it("enqueues and counts pending receipts", async () => {
    await enqueue({ trip_code: "T1", exp_type: "FUEL", amount: 1000 });
    await enqueue({ trip_code: "T1", exp_type: "TOLL", amount: 320 });
    expect(await pendingCount()).toBe(2);
    expect(await loadQueue()).toHaveLength(2);
  });

  it("drains successfully-posted items and keeps network-failed ones", async () => {
    await enqueue({ trip_code: "T1", exp_type: "FUEL", amount: 1000 });
    await enqueue({ trip_code: "T1", exp_type: "TOLL", amount: 320 });
    const post = vi
      .fn()
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new TypeError("Failed to fetch"));
    const res = await drain(post);
    expect(res.synced).toBe(1);
    expect(res.failed).toBe(1);
    expect(await pendingCount()).toBe(1);
  });

  it("drops non-network rejections so they don't wedge the queue", async () => {
    await enqueue({ trip_code: "T1", exp_type: "FUEL", amount: -1 });
    const post = vi.fn().mockRejectedValue({ status: 400, code: "INVALID_AMOUNT" });
    await drain(post);
    expect(await pendingCount()).toBe(0);
  });

  it("isNetworkError distinguishes fetch failures from HTTP errors", () => {
    expect(isNetworkError(new TypeError("Failed to fetch"))).toBe(true);
    expect(isNetworkError({ status: 400 })).toBe(false);
    expect(isNetworkError({ status: 500 })).toBe(false);
  });
});
