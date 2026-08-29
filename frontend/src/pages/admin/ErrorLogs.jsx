import { useEffect, useState } from "react";
import { api } from "../../lib/api.js";
import { useToast } from "../../context/ToastContext.jsx";
import Loader from "../../components/Loader.jsx";

const TYPE_COLORS = {
  INTERNAL: "bg-red-100 text-red-700",
  API_ERROR: "bg-amber-100 text-amber-700",
  VALIDATION: "bg-blue-100 text-blue-700",
  HTTP_ERROR: "bg-ink-100 text-ink-700",
};
const PAGE_SIZE = 20;

export default function ErrorLogsPage() {
  const toast = useToast();
  const [data, setData] = useState({ groups: [], total_groups: 0, total_occurrences: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sort, setSort] = useState("count");
  const [page, setPage] = useState(0);
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(null);

  function load(p = page, s = sort) {
    setLoading(true);
    api
      .get(`/api/v1/error-logs?sort=${s}&limit=${PAGE_SIZE}&offset=${p * PAGE_SIZE}`)
      .then(setData)
      .catch((e) => {
        setError(e.message);
        toast.error(e.message);
      })
      .finally(() => setLoading(false));
  }
  useEffect(() => {
    load(0, sort);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function changeSort(next) {
    setSort(next);
    setPage(0);
    load(0, next);
  }

  async function removeGroup(g) {
    if (!window.confirm(`Delete all ${g.count} occurrence(s) of this error?`)) return;
    setBusy(true);
    try {
      await api.del(
        `/api/v1/error-logs?endpoint=${encodeURIComponent(g.endpoint)}&error_type=${encodeURIComponent(g.error_type)}&status_code=${g.status_code}&message=${encodeURIComponent(g.message)}`
      );
      toast.success("Error group removed.");
      load();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function clearAll() {
    if (!window.confirm("Clear ALL error logs? This cannot be undone.")) return;
    setBusy(true);
    try {
      const res = await api.post("/api/v1/error-logs/clear");
      toast.success(`Cleared ${res.cleared ?? 0} log row(s).`);
      setPage(0);
      load(0, sort);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  }

  const totalPages = Math.max(1, Math.ceil((data.total_groups || 0) / PAGE_SIZE));

  // ---- Raw rows (full error_logs data) -------------------------------------
  const [view, setView] = useState("grouped"); // grouped | rows
  const [rowsData, setRowsData] = useState({ rows: [], total: 0 });
  const [rowsPage, setRowsPage] = useState(0);
  const [modalGroup, setModalGroup] = useState(null);
  const [modalData, setModalData] = useState({ rows: [], total: 0 });
  const [modalPage, setModalPage] = useState(0);
  const [openRowId, setOpenRowId] = useState(null);

  function groupQuery(g) {
    return g
      ? `&endpoint=${encodeURIComponent(g.endpoint)}&error_type=${encodeURIComponent(g.error_type)}&status_code=${g.status_code}&message=${encodeURIComponent(g.message)}`
      : "";
  }

  function loadRows(p = rowsPage, g = null, target = "page") {
    const qs = `/api/v1/error-logs/rows?limit=${PAGE_SIZE}&offset=${p * PAGE_SIZE}${groupQuery(g)}`;
    const setter = target === "modal" ? setModalData : setRowsData;
    setLoading(true);
    api
      .get(qs)
      .then((d) => {
        setter(d);
        setOpenRowId(null);
      })
      .catch((e) => toast.error(e.message))
      .finally(() => setLoading(false));
  }

  function switchView(v) {
    setView(v);
    if (v === "rows" && rowsData.rows.length === 0) loadRows(0);
  }

  function openGroup(g) {
    setModalGroup(g);
    setModalPage(0);
    loadRows(0, g, "modal");
  }

  const rowsTotalPages = Math.max(1, Math.ceil((rowsData.total || 0) / PAGE_SIZE));
  const modalTotalPages = Math.max(1, Math.ceil((modalData.total || 0) / PAGE_SIZE));
  return (
    <main className="space-y-6 p-4 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink-900">Error Logs</h1>
          <p className="mt-1 text-sm text-ink-500">
            {data.total_groups} distinct error group(s) · {data.total_occurrences} total
            occurrence(s)
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex overflow-hidden rounded-lg border border-ink-200" role="tablist" aria-label="Error view mode">
            <button
              type="button"
              role="tab"
              aria-selected={view === "grouped"}
              onClick={() => switchView("grouped")}
              className={`px-3 py-1.5 text-sm font-medium transition-all duration-200 ${view === "grouped" ? "bg-brand-600 text-white" : "bg-white text-ink-600 hover:bg-ink-50"}`}
            >
              Grouped
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={view === "rows"}
              onClick={() => switchView("rows")}
              className={`px-3 py-1.5 text-sm font-medium transition-all duration-200 ${view === "rows" ? "bg-brand-600 text-white" : "bg-white text-ink-600 hover:bg-ink-50"}`}
            >
              All Rows ({data.total_occurrences})
            </button>
          </div>
          <label className="flex items-center gap-2 text-sm text-ink-600">
            Sort by
            <select
              value={sort}
              onChange={(e) => changeSort(e.target.value)}
              aria-label="Sort errors"
              className="rounded-lg border border-ink-200 bg-white px-2 py-1.5 text-sm transition-all duration-200 focus:border-brand-500 focus:outline-none"
            >
              <option value="count">Count</option>
              <option value="last_seen">Last seen</option>
            </select>
          </label>
          <button
            type="button"
            onClick={clearAll}
            disabled={busy}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-all duration-200 hover:bg-red-700 disabled:opacity-50"
          >
            Clear Logs
          </button>
        </div>
      </div>

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {view === "grouped" && (
      <section className="overflow-hidden rounded-xl border border-ink-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader />
          </div>
        ) : data.groups.length === 0 ? (
          <p className="px-4 py-12 text-center text-sm text-ink-500">
            No errors logged. 🎉
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-ink-200 text-sm">
              <thead className="bg-ink-50 text-left text-xs font-semibold uppercase tracking-wider text-ink-500">
                <tr>
                  <th className="px-4 py-3">Count</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Message</th>
                  <th className="px-4 py-3">Endpoint</th>
                  <th className="px-4 py-3">Last seen</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100">
                {data.groups.map((g, i) => (
                  <tr key={`${g.endpoint}|${g.error_type}|${g.status_code}|${g.message}`} className="transition-all duration-200 hover:bg-ink-50">
                    <td className="px-4 py-3 font-bold text-ink-900">{g.count}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${TYPE_COLORS[g.error_type] || "bg-ink-100 text-ink-700"}`}>
                        {g.error_type} · {g.status_code}
                      </span>
                    </td>
                    <td className="max-w-xs px-4 py-3">
                      <button
                        type="button"
                        className="truncate text-left text-ink-800 hover:text-brand-700"
                        onClick={() => setExpanded(expanded === i ? null : i)}
                        title="Click to expand/collapse full message"
                      >
                        {expanded === i ? g.message : g.message.length > 80 ? `${g.message.slice(0, 80)}…` : g.message}
                      </button>
                    </td>
                    <td className="max-w-[12rem] truncate px-4 py-3 font-mono text-xs text-ink-600">{g.endpoint}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-ink-500">{g.last_seen}</td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        aria-label="View all raw log rows for this error group"
                        disabled={busy}
                        onClick={() => openGroup(g)}
                        className="rounded-lg px-2 py-1 text-brand-600 transition-all duration-200 hover:bg-brand-50 hover:text-brand-700 disabled:opacity-50"
                      >
                        👁
                      </button>
                      <button
                        type="button"
                        aria-label="Remove this error group"
                        disabled={busy}
                        onClick={() => removeGroup(g)}
                        className="rounded-lg px-2 py-1 text-red-600 transition-all duration-200 hover:bg-red-50 hover:text-red-700 disabled:opacity-50"
                      >
                        🗑
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      )}

      {view === "grouped" ? (
        <div className="flex items-center justify-between">
        <button
          type="button"
          disabled={page === 0 || loading}
          onClick={() => { const p = page - 1; setPage(p); load(p, sort); }}
          className="rounded-lg border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 transition-all duration-200 hover:bg-ink-50 disabled:opacity-50"
        >
          ← Previous
        </button>
        <span className="text-sm text-ink-500">
          Page {page + 1} of {totalPages}
        </span>
        <button
          type="button"
          disabled={page + 1 >= totalPages || loading}
          onClick={() => { const p = page + 1; setPage(p); load(p, sort); }}
          className="rounded-lg border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 transition-all duration-200 hover:bg-ink-50 disabled:opacity-50"
        >
          Next →
        </button>
      </div>
      ) : (
        <div className="flex items-center justify-between">
          <button
            type="button"
            disabled={rowsPage === 0 || loading}
            onClick={() => { const p = rowsPage - 1; setRowsPage(p); loadRows(p); }}
            className="rounded-lg border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 transition-all duration-200 hover:bg-ink-50 disabled:opacity-50"
          >
            ← Previous
          </button>
          <span className="text-sm text-ink-500">
            {rowsData.total} row(s) · Page {rowsPage + 1} of {rowsTotalPages}
          </span>
          <button
            type="button"
            disabled={rowsPage + 1 >= rowsTotalPages || loading}
            onClick={() => { const p = rowsPage + 1; setRowsPage(p); loadRows(p); }}
            className="rounded-lg border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 transition-all duration-200 hover:bg-ink-50 disabled:opacity-50"
          >
            Next →
          </button>
        </div>
      )}

      {modalGroup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/50 p-4" onClick={() => setModalGroup(null)}>
          <div className="max-h-[85vh] w-full max-w-5xl overflow-y-auto rounded-xl bg-white p-4 shadow-xl sm:p-6" onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold tracking-tight text-ink-900">
                  Error rows ({modalData.total}) — {modalGroup.error_type} · {modalGroup.status_code}
                </h2>
                <p className="mt-1 break-all font-mono text-xs text-ink-500">
                  {modalGroup.endpoint} — {modalGroup.message}
                </p>
              </div>
              <button
                type="button"
                aria-label="Close error rows"
                onClick={() => setModalGroup(null)}
                className="rounded-lg px-2 py-1 text-ink-500 transition-all duration-200 hover:bg-ink-100 hover:text-ink-900"
              >
                ✕
              </button>
            </div>
            <RawRowsTable
              rows={modalData.rows}
              loading={loading}
              emptyText="No rows in this group."
              openRowId={openRowId}
              setOpenRowId={setOpenRowId}
            />
            <div className="mt-4 flex items-center justify-between">
              <button
                type="button"
                disabled={modalPage === 0 || loading}
                onClick={() => { const p = modalPage - 1; setModalPage(p); loadRows(p, modalGroup, "modal"); }}
                className="rounded-lg border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 transition-all duration-200 hover:bg-ink-50 disabled:opacity-50"
              >
                ← Previous
              </button>
              <span className="text-sm text-ink-500">
                Page {modalPage + 1} of {modalTotalPages}
              </span>
              <button
                type="button"
                disabled={modalPage + 1 >= modalTotalPages || loading}
                onClick={() => { const p = modalPage + 1; setModalPage(p); loadRows(p, modalGroup, "modal"); }}
                className="rounded-lg border border-ink-200 bg-white px-4 py-2 text-sm font-medium text-ink-700 transition-all duration-200 hover:bg-ink-50 disabled:opacity-50"
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function RawRowsTable({ rows, loading, emptyText, openRowId, setOpenRowId }) {
  if (loading) {
    return (
      <div className="flex justify-center rounded-xl border border-ink-200 bg-white py-12 shadow-sm">
        <Loader />
      </div>
    );
  }
  if (rows.length === 0) {
    return (
      <p className="rounded-xl border border-ink-200 bg-white px-4 py-12 text-center text-sm text-ink-500 shadow-sm">
        {emptyText}
      </p>
    );
  }
  return (
    <div className="overflow-hidden rounded-xl border border-ink-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-ink-200 text-sm">
          <thead className="bg-ink-50 text-left text-xs font-semibold uppercase tracking-wider text-ink-500">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">When</th>
              <th className="px-4 py-3">Request</th>
              <th className="px-4 py-3">Type · Status</th>
              <th className="px-4 py-3">Message</th>
              <th className="px-4 py-3">Request ID</th>
              <th className="px-4 py-3">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-100">
            {rows.map((r) => {
              const open = openRowId === r.id;
              return (
                <tr key={r.id} className="transition-all duration-200 hover:bg-ink-50">
                  <td className="px-4 py-3 font-mono text-xs text-ink-500">#{r.id}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-ink-600">{r.created_at}</td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-700">
                    {r.method ? `${r.method} ` : ""}
                    <span className="break-all">{r.path || "—"}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${TYPE_COLORS[r.error_type] || "bg-ink-100 text-ink-700"}`}>
                      {r.error_type} · {r.status_code}
                    </span>
                  </td>
                  <td className="max-w-sm px-4 py-3">
                    <button
                      type="button"
                      className="break-all text-left text-ink-800 hover:text-brand-700"
                      onClick={() => setOpenRowId(open ? null : r.id)}
                      title={open ? "Hide full detail / traceback" : "Show full detail / traceback"}
                    >
                      {r.message}
                    </button>
                    {open && (
                      <div className="mt-2 space-y-2">
                        {r.endpoint && (
                          <p className="break-all text-xs text-ink-500">endpoint: <span className="font-mono">{r.endpoint}</span></p>
                        )}
                        {r.detail && (
                          <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-ink-50 p-2 text-xs text-ink-700">
                            {r.detail}
                          </pre>
                        )}
                        {r.traceback_text && (
                          <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-red-50 p-2 text-xs text-red-700">
                            {r.traceback_text}
                          </pre>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-500">{r.request_id || "—"}</td>
                  <td className="px-4 py-3 text-xs text-ink-500">{r.source || "BACKEND"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
