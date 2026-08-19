"""Fuel benchmarks CRUD `/api/v1` router.

GET is open to any authenticated user (read-only list); writes (create/update/
delete) require `super_admin`.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.app.core.security import require_json_auth, require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.benchmarks import (
    delete_benchmark,
    get_all_benchmarks,
    insert_benchmark,
    update_benchmark,
)

from backend.app.api.v1.deps import _bad, _created, _not_found, _ok
from backend.app.schemas.api_v1 import Data, ResourceAck

router = APIRouter(prefix="/api/v1")


@router.get("/benchmarks", response_model=Data[list[dict[str, Any]]])
def api_get_benchmarks(request: Request):
    guard = require_json_auth(request)
    if guard is not None:
        return guard
    with get_db() as conn:
        benchmarks = get_all_benchmarks(conn)
    return _ok(benchmarks)


@router.post("/benchmarks", response_model=Data[ResourceAck])
async def api_create_benchmark(request: Request):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    state_code = str(body.get("state_code", "")).strip().upper()
    state_name = str(body.get("state_name", "")).strip()
    if not state_code or not state_name:
        return _bad("state_code and state_name are required", "MISSING_FIELDS")
    price = float(body.get("benchmark_price_per_liter", 0.0))
    tolerance = float(body.get("tolerance_pct", 8.0))
    effective_date = body.get("effective_date") or None
    with get_db() as conn:
        new_id = insert_benchmark(
            conn, state_code, state_name, price, tolerance, effective_date
        )
    return _created({"id": new_id})


@router.put("/benchmarks/{bid}", response_model=Data[ResourceAck])
async def api_update_benchmark(request: Request, bid: int):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _bad("invalid JSON body")
    if not isinstance(body, dict):
        return _bad("body must be a JSON object")
    state_code = str(body.get("state_code", "")).strip().upper()
    state_name = str(body.get("state_name", "")).strip()
    if not state_code or not state_name:
        return _bad("state_code and state_name are required", "MISSING_FIELDS")
    price = float(body.get("benchmark_price_per_liter", 0.0))
    tolerance = float(body.get("tolerance_pct", 8.0))
    effective_date = body.get("effective_date") or None
    with get_db() as conn:
        ok = update_benchmark(
            conn, bid, state_code, state_name, price, tolerance, effective_date
        )
    if not ok:
        return _not_found("benchmark not found")
    return _ok({"id": bid})


@router.delete("/benchmarks/{bid}", status_code=204, response_model=None)
def api_delete_benchmark(request: Request, bid: int):
    guard = require_json_role(request, "super_admin")
    if guard is not None:
        return guard
    with get_db() as conn:
        ok = delete_benchmark(conn, bid)
    if not ok:
        return _not_found("benchmark not found")
    return JSONResponse(status_code=204, content=None)