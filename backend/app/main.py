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

# ---- No-cache guard ----------------------------------------------------------
# Force every response (backend APIs, SPA HTML, hashed assets, webhook callbacks)
# to bypass HTTP caches entirely: `no-store` forbids storing the response anywhere,
# which guarantees the latest deployed page + backend code is always served in
# production. Applied as the outermost middleware so it wraps ALL routes and
# mounted sub-apps.
_HTML_NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


@app.middleware("http")
async def _no_cache_everything(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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
          no-store, no-cache, must-revalidate, max-age=0` so the browser never
          stores it and always serves the newest build on reload.
        - For non-HTML static files (hashed JS/CSS/fonts) we also send
          `no-store` too and rely on Vite's content-hashed filenames for
          cache-busting: a changed build produces a new filename, so the new
          asset is always fetched with no stale-UI risk. The outer no-cache
          middleware guarantees no layer (browser, CDN, render proxy) caches
          any response.
        """
        if path and (_FRONTEND_DIST / path).is_file():
            return FileResponse(
                _FRONTEND_DIST / path,
                headers=_HTML_NO_CACHE,
            )
        return HTMLResponse(
            _STATIC_INDEX.read_text(encoding="utf-8"),
            status_code=200,
            headers=_HTML_NO_CACHE,
        )