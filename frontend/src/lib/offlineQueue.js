// Offline expense queue — receipts logged while offline are parked here and
// POSTed to /api/v1/expenses when connectivity returns (or on next boot).
//
// Backed by IndexedDB (not localStorage) so large receipt photos (base64 data
// URLs) are not bounded by the ~5 MB localStorage quota.

const DB_NAME = "vk_offline_queue";
const STORE = "receipts";

function openDb() {
  return new Promise((resolve, reject) => {
    if (!globalThis.indexedDB) {
      reject(new Error("IndexedDB unavailable"));
      return;
    }
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// Run a single-request transaction; resolves with the request's result after
// the transaction commits, and always closes the connection.
function withStore(mode, fn) {
  return openDb().then(
    (db) =>
      new Promise((resolve, reject) => {
        const tx = db.transaction(STORE, mode);
        const store = tx.objectStore(STORE);
        const req = fn(store);
        tx.oncomplete = () => {
          db.close();
          resolve(req.result);
        };
        tx.onerror = () => {
          db.close();
          reject(tx.error);
        };
        tx.onabort = () => {
          db.close();
          reject(tx.error);
        };
      }),
  );
}

export function loadQueue() {
  return withStore("readonly", (store) => store.getAll()).catch(() => []);
}

export async function enqueue(payload) {
  const id =
    (globalThis.crypto && crypto.randomUUID && crypto.randomUUID()) ||
    `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  try {
    await withStore("readwrite", (store) =>
      store.add({ id, payload, queued_at: Date.now() }),
    );
  } catch {
    /* IndexedDB unavailable — best-effort */
  }
  return id;
}

export async function pendingCount() {
  const queue = await loadQueue();
  return queue.length;
}

// Replay the queue in order. `post` is `(payload) => Promise`. A network error
// (no HTTP status) keeps the item for a later retry; any other rejection
// (validation/auth — an ApiError with a numeric status) is dropped so it can't
// wedge the queue forever.
export async function drain(post) {
  const queue = await loadQueue();
  let synced = 0;
  const failed = [];
  for (const item of queue) {
    try {
      await post(item.payload);
      synced += 1;
      await remove(item.id);
    } catch (err) {
      if (!isNetworkError(err)) await remove(item.id);
      failed.push(item.id);
    }
  }
  return { synced, failed: failed.length };
}

function remove(id) {
  return withStore("readwrite", (store) => store.delete(id));
}

// Offline fetch rejects with a bare TypeError (no status); api.js's ApiError
// carries a numeric `status` for HTTP errors. Only network failures retry.
export function isNetworkError(err) {
  return !(err && typeof err === "object" && typeof err.status === "number");
}
