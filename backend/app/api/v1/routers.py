from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1 import (
    auth,
    benchmarks,
    billing,
    dashboard,
    expenses,
    fleets,
    onboard,
    states,
    trips,
    users,
    vehicles,
    whatsapp,
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
    onboard.router,
    whatsapp.router,
    states.router,
)

for _r in _DOMAIN_ROUTERS:
    router.include_router(_r)

__all__ = ["router"]