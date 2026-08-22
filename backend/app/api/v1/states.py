"""Reference endpoint exposing the canonical Indian state list to clients.

The driver-submitted fuel expense needs a fueling-state dropdown; this returns
the shared, server-authoritative list so the driver picks a valid state_code
that the rules engine can look up in `fuel_benchmarks`.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from backend.app.api.v1.deps import _ok
from backend.app.core.security import get_current_user, require_json_auth
from backend.app.db.connection import get_db
from backend.app.db.queries.benchmarks import (
    get_benchmark_states,
    get_favorite_state_codes,
)
from backend.app.schemas.api_v1 import Data
from backend.app.services.states import INDIAN_STATES, STATE_NAME_BY_CODE

router = APIRouter(prefix="/api/v1")

# Only operating state offered while fuel_benchmarks has no rows yet.
_FALLBACK_STATE = "UP"


@router.get("/states", response_model=Data[list[dict[str, Any]]])
def api_list_states(request: Request, source: str = "canonical"):
    """Return `[{code, name, is_favorite}]` for client state pickers.

    `is_favorite` mirrors the caller's Rules & Rates favorites so dropdowns can
    pin starred states to the top without a second round-trip.

    `source=benchmarks` serves the **DB-driven** fueling-state list: only states
    present in `fuel_benchmarks` (so the rules engine can always price whatever
    gets picked), falling back to UP alone while that table is still empty. The
    default keeps the full canonical list from `services/states.py`.
    """
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        if (source or "").strip().lower() == "benchmarks":
            rows = get_benchmark_states(conn, user["user_id"])
            if rows:
                return _ok(
                    [
                        {
                            "code": r["state_code"],
                            "name": r["state_name"],
                            "is_favorite": bool(r["is_favorite"]),
                        }
                        for r in rows
                    ]
                )
            # Empty benchmarks table: offer only the default operating state.
            favorites = set(get_favorite_state_codes(conn, user["user_id"]))
            return _ok(
                [
                    {
                        "code": _FALLBACK_STATE,
                        "name": STATE_NAME_BY_CODE[_FALLBACK_STATE],
                        "is_favorite": _FALLBACK_STATE in favorites,
                    }
                ]
            )
        favorites = set(get_favorite_state_codes(conn, user["user_id"]))
    return _ok(
        [
            {"code": c, "name": n, "is_favorite": c in favorites}
            for c, n in INDIAN_STATES
        ]
    )
