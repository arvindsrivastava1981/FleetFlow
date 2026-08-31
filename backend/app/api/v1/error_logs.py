"""Super Admin error-log management endpoints (error_logs table).

All routes are super_admin-only (403 for every other role). The read model is
a grouped summary — each row is one distinct error (endpoint + type + status
+ message) with its occurrence count and last-seen timestamp — which is what
the `/error-logs` SPA page renders.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.api.v1.deps import _ok, _page_params
from backend.app.core.errors import not_found
from backend.app.core.security import require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.error_logs import (
    clear_error_logs,
    count_error_rows,
    delete_error_group,
    list_error_groups,
    list_error_rows,
)

router = APIRouter(prefix="/api/v1")


@router.get("/error-logs")
def api_error_logs(request: Request):
    """Grouped error summary: count, type, message, endpoint, last seen.

    Query params: ``limit`` (default 20, cap 200), ``offset``, ``sort``
    (``count`` | ``last_seen``). super_admin only.
    """
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    qp = request.query_params
    sort = qp.get("sort", "count")
    if sort not in ("count", "last_seen"):
        sort = "count"
    limit, offset = _page_params(request, default_limit=20, max_limit=200)
    with get_db() as conn:
        data = list_error_groups(conn, limit=limit, offset=offset, sort=sort)
    data["limit"], data["offset"], data["sort"] = limit, offset, sort
    return _ok(data)


@router.get("/error-logs/rows")
def api_error_log_rows(request: Request):
    """Raw `error_logs` rows (every column), newest first.

    Optional group filters (``endpoint`` / ``error_type`` / ``status_code`` /
    ``message``) narrow to one group; omit them for the full table. Pagination
    via ``limit`` (default 20, cap 200) + ``offset``; total returned in
    ``total``. super_admin only.
    """
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    qp = request.query_params
    limit, offset = _page_params(request, default_limit=20, max_limit=200)
    endpoint = (qp.get("endpoint") or "").strip() or None
    error_type = (qp.get("error_type") or "").strip() or None
    message = (qp.get("message") or "").strip() or None
    try:
        status_code = int(qp.get("status_code", ""))
    except ValueError:
        status_code = None
    with get_db() as conn:
        rows = list_error_rows(
            conn,
            limit=limit,
            offset=offset,
            endpoint=endpoint,
            error_type=error_type,
            status_code=status_code,
            message=message,
        )
        total = count_error_rows(
            conn,
            endpoint=endpoint,
            error_type=error_type,
            status_code=status_code,
            message=message,
        )
    return _ok({"rows": rows, "total": total, "limit": limit, "offset": offset})


@router.delete("/error-logs")
def api_error_log_delete(request: Request):
    """Delete one error group (all rows sharing endpoint/type/status/message)."""
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    qp = request.query_params
    endpoint = (qp.get("endpoint") or "").strip()
    error_type = (qp.get("error_type") or "").strip()
    message = (qp.get("message") or "").strip()
    try:
        status_code = int(qp.get("status_code", ""))
    except ValueError:
        status_code = -1
    if not endpoint or not error_type:
        raise not_found("error group not found")
    with get_db() as conn:
        deleted = delete_error_group(
            conn,
            endpoint=endpoint,
            error_type=error_type,
            status_code=status_code,
            message=message,
        )
    if deleted == 0:
        raise not_found("error group not found")
    return _ok({"deleted": deleted})


@router.post("/error-logs/clear")
def api_error_logs_clear(request: Request):
    """Clear the entire error log (all rows). super_admin only."""
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    with get_db() as conn:
        deleted = clear_error_logs(conn)
    return _ok({"cleared": deleted})
