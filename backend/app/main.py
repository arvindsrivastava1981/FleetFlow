"""FleetFlow application entrypoint (FastAPI factory).

Primary deploy target (see Dockerfile / render.yaml / start.ps1):
    uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}

All routes from the legacy `fleetflow_interactive_demo.py` prototype have been
migrated into `backend/app/api/*` routers wired below. The prototype file and
`utils.py` have been removed (see APP_MINDMAP.md / PROJECT_STRUCTURE.md).
"""
from __future__ import annotations

from fastapi import FastAPI

from backend.app.api import (
    auth,
    benchmarks,
    dashboard,
    demo,
    expenses,
    rule_engine,
    settlement,
    trips,
    views,
)
from backend.app.db.connection import healthcheck

app = FastAPI(
    title="FleetFlow",
    description="Real-Time Fleet Expense Verification & Settlement Engine",
    version="0.1.0",
)

# ---- Routers (auth/mutations first, then read-only UI pages) ----------------
app.include_router(auth.router)
app.include_router(trips.router)
app.include_router(expenses.router)
app.include_router(demo.router)
app.include_router(dashboard.router)
app.include_router(benchmarks.router)
app.include_router(rule_engine.router)
app.include_router(settlement.router)
app.include_router(views.router)


@app.get("/healthz")
def healthz() -> dict:
    """Liveness + DB reachability probe for Render/Docker health checks."""
    return {"status": "ok", **healthcheck()}