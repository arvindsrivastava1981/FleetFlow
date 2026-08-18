"""Tests for the JSON-only backend + SPA-fallback architecture.

All server-rendered HTML routers were removed from the backend (`views.py`,
`auth.py`, `benchmarks.py`, `settlement.py`, `rule_engine.py`, `vehicles.py`,
`users.py`, `dashboards.py`, etc.). `main.py` mounts only the `/api/v1` JSON
router, the Razorpay webhook, and the built React SPA (catch-all -> index.html).

These tests assert:
- every legacy HTML page path now falls through to the SPA index (no backend
  HTML generation),
- the `/api/v1` JSON endpoints keep returning 401 (not 303) when unauthenticated,
- the app exposes no module for the removed routers.
"""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app, follow_redirects=False)

# Legacy server-rendered HTML paths that used to render Django-style pages.
LEGACY_HTML_GET_PATHS = [
    "/",
    "/trips",
    "/fuel-benchmarks",
    "/settled-pdfs",
    "/rule-engine",
    "/users/change-password",
    "/vehicles",
    "/admin",
    "/manager",
    "/driver",
]


def test_legacy_get_pages_fall_through_to_spa_index():
    """Every removed HTML page is now served by the React SPA catch-all."""
    for path in LEGACY_HTML_GET_PATHS:
        resp = client.get(path, follow_redirects=True)
        assert resp.status_code == 200, path
        assert "text/html" in resp.headers["content-type"], path


def test_no_module_for_removed_html_routers():
    """The dead HTML router source files no longer exist in `backend/app/api`."""
    api_dir = Path(__file__).resolve().parents[1].parent / "backend" / "app" / "api"
    existing = {p.stem for p in api_dir.glob("*.py")}
    removed = {
        "views", "auth", "dashboard", "dashboards", "trips", "expenses",
        "settlement", "rule_engine", "vehicles", "users", "drivers",
        "fleets", "benchmarks", "billing",
    }
    assert removed.isdisjoint(existing)


# ---- JSON API guardrails (unchanged behavior verified by test_auth_routes.py) --
def test_api_v1_endpoints_return_json_when_unauthenticated():
    """The JSON API returns 401 JSON (never 303) for unauthenticated requests."""
    for path in ("/api/v1/trips", "/api/v1/dashboard/overview", "/api/v1/fleets"):
        resp = client.get(path)
        assert resp.status_code == 401, path
        assert "application/json" in resp.headers["content-type"], path


def test_api_v1_never_redirects_to_login():
    """A 303 redirect to /login must never come from an /api/v1 endpoint."""
    resp = client.get("/api/v1/trips")
    assert resp.status_code == 401
    assert resp.headers.get("location") is None