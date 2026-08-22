from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import (
    api_v1,
    webhook,
)
from backend.app.core.config import settings
from backend.app.core.errors import register_error_handlers
from backend.app.db.connection import healthcheck

app = FastAPI(
    title="VahanKhata",
    description="Real-Time Fleet Expense Verification & Settlement Engine",
    version="0.1.0",
)

# ---- CORS -------------------------------------------------------------------
# Allow browser requests from the hosted web client (VahanKhata on Render) so
# clients can call these APIs cross-origin. Origins are env-driven via
# CORS_ORIGINS (CSV) with the historical allowlist as fallback — audit R-5.
# Wildcard is intentionally NOT used so credentials are never leaked to
# arbitrary origins.
CORS_ALLOWED_ORIGINS = settings.cors_origins

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


# ---- Global error handlers ---------------------------------------------------
# Install AFTER routes/middleware so every endpoint (and any uncaught 5xx)
# flows through the central error handlers, which persist failures into the
# `error_logs` table (see backend/app/core/errors.py).
register_error_handlers(app)
