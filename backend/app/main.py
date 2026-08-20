from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api import (
    api_v1,
    webhook,
)
from backend.app.core.errors import register_error_handlers
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
    "https://vahankhata-api.onrender.com",
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

# ---- No-cache guard ----------------------------------------------------------
# Force every response (backend APIs, webhook callbacks) to bypass HTTP caches
# entirely: `no-store` forbids storing the response anywhere, which guarantees
# the latest backend code is always served in production. Applied as the
# outermost middleware so it wraps ALL routes and mounted sub-apps.


@app.middleware("http")
async def _no_cache_everything(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ---- Routers (JSON API) -----------------------------------------------------
# The backend exposes the `/api/v1` JSON API and the Razorpay webhook callback.
# The legacy server-rendered HTML routers were removed; their JSON equivalents
# live in `api_v1.py`.
app.include_router(api_v1.router)
app.include_router(webhook.router)


@app.get("/healthz")
def healthz() -> dict:
    """Liveness + DB reachability probe for Render/Docker health checks."""
    return {"status": "ok", **healthcheck()}


# ---- Static SPA mount + client-route fallback -------------------------------
# The React SPA is compiled to `frontend/dist` and mounted at `/`. Client-side
# (Vite/BrowserRouter) routes like /login, /dashboard and /trips/:code have NO
# server-side HTML, so a hard refresh / direct hit to any of those paths must be
# answered with the SPA `index.html` for React Router to take over — otherwise
# the browser gets a 404. Mounting order matters: the concrete `/api/v1` and
# `/healthz` routes are registered ABOVE this, so they always win; the mount and
# the GET-only catch-all below only serve paths the API doesn't own. Non-GET
# requests (e.g. POST to a removed legacy HTML route) intentionally fall through
# the GET-only catch-all to the 405/404 handler rather than returning the SPA.
_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", response_model=None, include_in_schema=False)
    def _spa_fallback(full_path: str) -> FileResponse | HTMLResponse:
        candidate = (_DIST / full_path).resolve()
        # Serve real static files (favicon, etc.) if present, but never allow
        # escaping the dist dir via `..`.
        if candidate.is_file() and _DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        # Everything else is a client-side route -> return the SPA shell.
        return HTMLResponse((_DIST / "index.html").read_bytes())


# ---- Global error handlers ---------------------------------------------------
# Install AFTER routes/middleware so every endpoint (and any uncaught 5xx)
# flows through the central error handlers, which persist failures into the
# `error_logs` table (see backend/app/core/errors.py).
register_error_handlers(app)