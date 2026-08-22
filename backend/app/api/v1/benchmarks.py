from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from backend.app.core.security import (
    get_current_user,
    require_json_auth,
    require_json_role,
)
from backend.app.db.connection import get_db
from backend.app.db.queries.benchmarks import (
    add_benchmark_favorite,
    get_all_benchmarks,
    get_home_state,
    remove_benchmark_favorite,
    set_home_state,
    upsert_benchmarks_from_live,
)
from backend.app.services.fuel_live import get_live_prices
from backend.app.services.states import INDIAN_STATES

from backend.app.api.v1.deps import _bad, _ok
from backend.app.schemas.api_v1 import (
    BenchmarkFavoriteAck,
    Data,
    HomeStateResult,
)

router = APIRouter(prefix="/api/v1")

# Canonical RTO state codes (single source of truth: services.states).
_VALID_STATE_CODES = {code for code, _name in INDIAN_STATES}


def _normalise_state(state_code: str) -> str:
    """Uppercase + validate a client-supplied state code; raises 400 if unknown."""
    code = (state_code or "").strip().upper()
    if code not in _VALID_STATE_CODES:
        _bad(f"unknown state_code: {code!r}", "INVALID_STATE")
    return code


@router.get("/benchmarks", response_model=Data[dict[str, Any]])
def api_get_benchmarks(request: Request):
    """Rules & Rates payload: every state benchmark tagged with the caller's
    `is_favorite` flag, plus their usual operating state (`home_state_code`)."""
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        benchmarks = get_all_benchmarks(conn, user_id=user["user_id"])
        home_state = get_home_state(conn, user["user_id"])
    return _ok({"benchmarks": benchmarks, "home_state_code": home_state})


@router.post(
    "/benchmarks/{state_code}/favorite", response_model=Data[BenchmarkFavoriteAck]
)
def api_add_benchmark_favorite(state_code: str, request: Request):
    """Add a state to the caller's favorites (any authenticated role)."""
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    code = _normalise_state(state_code)
    with get_db() as conn:
        add_benchmark_favorite(conn, get_current_user(request)["user_id"], code)
    return _ok({"state_code": code, "is_favorite": True})


@router.delete(
    "/benchmarks/{state_code}/favorite", response_model=Data[BenchmarkFavoriteAck]
)
def api_remove_benchmark_favorite(state_code: str, request: Request):
    """Remove a state from the caller's favorites."""
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    code = _normalise_state(state_code)
    with get_db() as conn:
        remove_benchmark_favorite(conn, get_current_user(request)["user_id"], code)
    return _ok({"state_code": code, "is_favorite": False})


@router.put("/benchmarks/home-state", response_model=Data[HomeStateResult])
async def api_set_home_state(request: Request):
    """Store/clear the caller's usual operating state (`users.home_state_code`).

    Body ``{"state_code": "UP"}``; an empty/missing value clears it. The code is
    validated against the canonical INDIAN_STATES list server-side.
    """
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    raw = str((body or {}).get("state_code") or "").strip()
    code = _normalise_state(raw) if raw else None
    with get_db() as conn:
        set_home_state(conn, get_current_user(request)["user_id"], code)
    return _ok({"home_state_code": code})


@router.post("/benchmarks/sync-live", response_model=Data[dict[str, Any]])
async def api_sync_benchmarks(request: Request):
    """Fetch live state-level diesel prices and upsert them into fuel_benchmarks.

    Super Admin / Trip Manager only. Best-effort: tries the goodreturns live
    page first and falls back to a maintained static snapshot when the page is
    unreachable or unparsable. Returns how many rows were updated plus the
    fetched source.
    """
    guard = require_json_role(request, "super_admin", "trip_manager")
    if guard is not None:
        return guard
    rows = get_live_prices()
    with get_db() as conn:
        touched = upsert_benchmarks_from_live(conn, rows)
    return _ok(
        {
            "updated": touched,
            "states": [r["state_code"] for r in rows],
            "source": "goodreturns|static",
        }
    )