from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from backend.app.core.security import require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.benchmarks import (
    get_all_benchmarks,
    upsert_benchmarks_from_live,
)
from backend.app.services.fuel_live import get_live_prices

from backend.app.api.v1.deps import _ok
from backend.app.schemas.api_v1 import Data

router = APIRouter(prefix="/api/v1")


@router.get("/benchmarks", response_model=Data[list[dict[str, Any]]])
def api_get_benchmarks(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    with get_db() as conn:
        benchmarks = get_all_benchmarks(conn)
    return _ok(benchmarks)


@router.post("/benchmarks/sync-live", response_model=Data[dict[str, Any]])
async def api_sync_benchmarks(request: Request):
    """Fetch live state-level diesel prices and upsert them into fuel_benchmarks.

    Super Admin only. Best-effort: tries the goodreturns live page first and
    falls back to a maintained static snapshot when the page is unreachable or
    unparsable. Returns how many rows were updated plus the fetched source.
    """
    guard = require_json_role(request, "super_admin")
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