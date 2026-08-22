"""Reference endpoint exposing the canonical Indian state list to clients.

The driver-submitted fuel expense needs a fueling-state dropdown; this returns
the shared, server-authoritative list so the driver picks a valid state_code
that the rules engine can look up in `fuel_benchmarks`.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from backend.app.core.security import get_current_user, require_json_auth
from backend.app.db.connection import get_db
from backend.app.db.queries.benchmarks import get_favorite_state_codes
from backend.app.services.states import INDIAN_STATES

from backend.app.api.v1.deps import _ok
from backend.app.schemas.api_v1 import Data

router = APIRouter(prefix="/api/v1")


@router.get("/states", response_model=Data[list[dict[str, Any]]])
def api_list_states(request: Request):
    """Return the canonical state list as [{code, name, is_favorite}].

    `is_favorite` mirrors the caller's Rules & Rates favorites so client
    dropdowns (driver fueling-state picker etc.) can pin starred states to the
    top without a second round-trip.
    """
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        favorites = set(get_favorite_state_codes(conn, user["user_id"]))
    return _ok(
        [
            {"code": c, "name": n, "is_favorite": c in favorites}
            for c, n in INDIAN_STATES
        ]
    )