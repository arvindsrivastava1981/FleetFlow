"""VahanKhata application entrypoint (FastAPI factory).

Primary deploy target (see Dockerfile / render.yaml / start.ps1):
    uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}

All routes from the legacy `fleetflow_interactive_demo.py` prototype have been
migrated into `backend/app/api/*` routers wired below. The prototype file and
`utils.py` have been removed (see APP_MINDMAP.md / PROJECT_STRUCTURE.md).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api import (
    api_v1,
    auth,
    benchmarks,
    billing,
    dashboard,
    dashboards,
    drivers,
    expenses,
    fleets,
    rule_engine,
    settlement,
    trips,
    users,
    vehicles,
    views,
)
from backend.app.db.connection import healthcheck

app = FastAPI(
    title="VahanKhata",
    description="Real-Time Fleet Expense Verification & Settlement Engine",
    version="0.1.0",
)

# ---- CORS -------------------------------------------------------------------
# Allow browser requests from the hosted frontend (VahanKhata on Render) so the
# SPA can call these APIs cross-origin. Local dev origins are included for
# convenience; wildcard is intentionally NOT used so credentials are never
# leaked to arbitrary origins.
CORS_ALLOWED_ORIGINS = [
    "https://vahankhata-app.onrender.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers (auth/mutations first, then read-only UI pages) ----------------
app.include_router(api_v1.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(drivers.router)
app.include_router(vehicles.router)
app.include_router(fleets.router)
app.include_router(billing.router)
app.include_router(trips.router)
app.include_router(expenses.router)
app.include_router(dashboard.router)
app.include_router(dashboards.router)
app.include_router(benchmarks.router)
app.include_router(rule_engine.router)
app.include_router(settlement.router)
app.include_router(views.router)


@app.get("/healthz")
def healthz() -> dict:
    """Liveness + DB reachability probe for Render/Docker health checks."""
    return {"status": "ok", **healthcheck()}


# ---- Static SPA mount (Phase 1) ---------------------------------------------
# Serve the compiled Vite/React frontend from `frontend/dist/` at "/" when it
# exists. Client-side routes (e.g. /trips/TRIP-101, /dashboard) fall back to
# index.html so React Router can resolve them without 404s.
#
# Note: define this AFTER all API/HTML routers so those explicit paths always win
# over the catch-all SPA fallback. Legacy HTML pages (server-rendered f-strings)
# remain fully intact and reachable.
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_STATIC_INDEX = _FRONTEND_DIST / "index.html"

if _FRONTEND_DIST.is_dir() and _STATIC_INDEX.is_file():
    # Serve hashed assets (files that genuinely exist) directly.
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIST / "assets")),
        name="spa-assets",
    )

    @app.get("/{path:path}", response_class=HTMLResponse, include_in_schema=False, response_model=None)
    def spa_fallback(request: Request, path: str):
        """Serve real static files, else fall back to the SPA index.html."""
        if path and (_FRONTEND_DIST / path).is_file():
            return FileResponse(_FRONTEND_DIST / path)
        return HTMLResponse(_STATIC_INDEX.read_text(encoding="utf-8"), status_code=200)