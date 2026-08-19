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

# ---- Routers (JSON API only) ------------------------------------------------
# All UI is served by the React SPA (`frontend/dist` mounted below). The backend
# exposes only the `/api/v1` JSON API and the Razorpay webhook callback. The
# legacy server-rendered HTML routers were removed; their JSON equivalents live
# in `api_v1.py`.
app.include_router(api_v1.router)
app.include_router(webhook.router)


@app.get("/healthz")
def healthz() -> dict:
    """Liveness + DB reachability probe for Render/Docker health checks."""
    return {"status": "ok", **healthcheck()}


# ---- Static SPA mount (Phase 1) ---------------------------------------------
# Serve the compiled Vite/React frontend from `frontend/dist/` at "/" when it
# exists. Client-side routes (e.g. /trips/TRIP-101, /dashboard) fall back to
# index.html so React Router can resolve them without 404s.
#
# Note: define this AFTER all API routes so explicit API paths (incl. the
# `/billing/webhook` callback) always win over the catch-all SPA fallback.
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
        """Serve real static files, else fall back to the SPA index.html.

        Cache strategy:
        - `index.html` (and every HTML document) returns `Cache-Control:
          no-cache` so the browser must revalidate on every reload and always
          picks up the newest bundle references (fresh UI). Hash-named assets
          are immutable, so they can be cached long-term.
        - For non-HTML static files (hashed JS/CSS/fonts) we send
          `Cache-Control: no-cache` too and rely on Vite's content-hashed
          filenames for cache-busting: a changed build produces a new filename,
          so revalidation yields the new immutable asset with no stale-UI risk.
        """
        if path and (_FRONTEND_DIST / path).is_file():
            return FileResponse(
                _FRONTEND_DIST / path,
                headers={"Cache-Control": "no-cache"},
            )
        return HTMLResponse(
            _STATIC_INDEX.read_text(encoding="utf-8"),
            status_code=200,
            headers={"Cache-Control": "no-cache"},
        )