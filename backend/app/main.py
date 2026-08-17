"""FleetFlow application entrypoint (FastAPI factory).

Target invocation after the router migration is complete:
    uvicorn backend.app.main:app

For the current incremental migration (prototype still live), run the existing
`fleetflow_interactive_demo.py` unchanged — nothing here is imported by it yet.
This module is the *destination* the routers in `backend/app/api/` get wired
into. Until a router is migrated, `app` exposes just a health probe and root so
the package boots cleanly and the structure is verifiable.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.app.api import auth, dashboard, demo, expenses, trips
from backend.app.core.config import settings
from backend.app.db.connection import healthcheck

app = FastAPI(
    title="FleetFlow",
    description="Real-Time Fleet Expense Verification & Settlement Engine",
    version="0.1.0",
)

# ---- Routers (security-critical mutations ported first) ---------------------
app.include_router(auth.router)
app.include_router(trips.router)
app.include_router(expenses.router)
app.include_router(demo.router)
app.include_router(dashboard.router)


@app.get("/healthz")
def healthz() -> dict:
    """Liveness + DB reachability probe for Render/Docker health checks."""
    return {"status": "ok", **healthcheck()}


@app.get("/")
def root(request: Request) -> JSONResponse:
    """Silence the safe mapping issue and return environment summary."""
    return JSONResponse(
        {
            "service": "fleetflow",
            "env": "production" if settings.is_production else "development",
            "docs": "/docs",
            "note": "Routes are migrated incrementally from the prototype into "
            "backend/app/api; ruff the resident prototypes until then.",
        }
    )