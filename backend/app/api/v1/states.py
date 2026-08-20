"""Reference endpoint exposing the canonical Indian state list to clients.

The driver-submitted fuel expense needs a fueling-state dropdown; this returns
the shared, server-authoritative list so the driver picks a valid state_code
that the rules engine can look up in `fuel_benchmarks`.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from backend.app.core.security import require_json_auth
from backend.app.services.states import INDIAN_STATES

from backend.app.api.v1.deps import _ok
from backend.app.schemas.api_v1 import Data

router = APIRouter(prefix="/api/v1")


@router.get("/states", response_model=Data[list[dict[str, str]]])
def api_list_states(request: Request):
    """Return the canonical state list as [{code, name}] for the fuel dropdown."""
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    return _ok([{"code": c, "name": n} for c, n in INDIAN_STATES])