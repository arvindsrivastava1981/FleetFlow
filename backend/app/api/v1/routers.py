"""Aggregate all `/api/v1` domain routers into one FastAPI router.

Each domain router uses `prefix="/api/v1"`, so mounting them here is a plain
`include_router(other)` — no stacked prefixes. `backend.app.api.api_v1`
re-exports this aggregated `router` for `main.py`.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1 import (
    auth,
    benchmarks,
    billing,
    dashboard,
    expenses,
    fleets,
    rules,
    trips,
    users,
    vehicles,
)

router = APIRouter()

_DOMAIN_ROUTERS = (
    dashboard.router,
    auth.router,
    trips.router,
    expenses.router,
    vehicles.router,
    fleets.router,
    users.router,
    benchmarks.router,
    billing.router,
    rules.router,
)

for _r in _DOMAIN_ROUTERS:
    router.include_router(_r)

__all__ = ["router"]