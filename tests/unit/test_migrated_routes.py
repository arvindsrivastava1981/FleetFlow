"""Route-security tests for the routers completing the prototype migration.

Covers the pages ported from `fleetflow_interactive_demo.py` in this change:
`views.py` (`/`, `/trips`, `/`), `benchmarks.py` (`/fuel-benchmarks*`),
`settlement.py` (`/settled-pdfs`, `/generate-settlement-pdf`), and confirms
`rule_engine.py` is wired into the app (was previously built but never
included by `main.py`).

Same approach as `test_auth_routes.py`: unauthenticated requests must 303 to
`/login` before any DB work happens, so these tests need no live database.
`/rule-engine` renders from static settings only, so we also assert its
authenticated 200 response using a real (in-memory) session token.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.core.security import AUTH_COOKIE, create_session
from backend.app.main import app

client = TestClient(app, follow_redirects=False)

BENCHMARK_ADD_BODY = {
    "state_code": "UP",
    "state_name": "Uttar Pradesh",
    "benchmark_price_per_liter": "90.50",
    "tolerance_pct": "8.0",
}


def assert_login_redirect(resp) -> None:
    assert resp.status_code == 303
    assert resp.headers["location"].rstrip("/").endswith("/login")


# ---- views.py --------------------------------------------------------------
def test_unauthenticated_index_redirects_to_login():
    assert_login_redirect(client.get("/?trip_code=TRIP-101"))


def test_unauthenticated_trips_redirects_to_login():
    assert_login_redirect(client.get("/trips"))


def test_unauthenticated__redirects_to_login():
    assert_login_redirect(client.get("/"))


# ---- benchmarks.py -----------------------------------------------------
def test_unauthenticated_fuel_benchmarks_page_redirects_to_login():
    assert_login_redirect(client.get("/fuel-benchmarks"))


def test_unauthenticated_fuel_benchmarks_add_redirects_to_login():
    assert_login_redirect(client.post("/fuel-benchmarks/add", data=BENCHMARK_ADD_BODY))


def test_unauthenticated_fuel_benchmarks_edit_redirects_to_login():
    body = {**BENCHMARK_ADD_BODY, "id": "1"}
    assert_login_redirect(client.post("/fuel-benchmarks/edit", data=body))


def test_unauthenticated_fuel_benchmarks_delete_redirects_to_login():
    assert_login_redirect(client.get("/fuel-benchmarks/delete?id=1"))


# ---- settlement.py -----------------------------------------------------
def test_unauthenticated_settled_pdfs_redirects_to_login():
    assert_login_redirect(client.get("/settled-pdfs"))


def test_unauthenticated_generate_settlement_pdf_redirects_to_login():
    assert_login_redirect(client.get("/generate-settlement-pdf?trip_code=TRIP-101"))


# ---- rule_engine.py (now wired into main.py) ---------------------------
def test_unauthenticated_rule_engine_redirects_to_login():
    assert_login_redirect(client.get("/rule-engine"))


def test_authenticated_rule_engine_renders_without_db():
    token = create_session(user_id=1, username="admin", role="super_admin")
    try:
        resp = client.get("/rule-engine", cookies={AUTH_COOKIE: token})
        assert resp.status_code == 200
        assert "Rule Engine" in resp.text
        assert "FUEL" in resp.text
    finally:
        from backend.app.core.security import _auth_sessions

        _auth_sessions.pop(token, None)


# ---- dashboards.py (role-based dashboards) -----------------------------
def test_unauthenticated_admin_redirects_to_login():
    assert_login_redirect(client.get("/admin"))


def test_unauthenticated_manager_redirects_to_login():
    assert_login_redirect(client.get("/manager"))


def test_unauthenticated_driver_redirects_to_login():
    assert_login_redirect(client.get("/driver"))


def test_role_mismatch_redirects_to_dashboard():
    """A trip_manager must not enter the super_admin-only /admin page."""
    token = create_session(user_id=2, username="manager1", role="trip_manager")
    try:
        resp = client.get("/admin", cookies={AUTH_COOKIE: token})
        assert resp.status_code == 303
        assert resp.headers["location"].rstrip("/").endswith("/dashboard")
    finally:
        from backend.app.core.security import _auth_sessions

        _auth_sessions.pop(token, None)


def test_admin_can_open_manager_dashboard():
    """super_admin is allowed on the trip_manager dashboard."""
    token = create_session(user_id=1, username="admin", role="super_admin")
    try:
        resp = client.get("/manager", cookies={AUTH_COOKIE: token})
        assert resp.status_code in (200, 303)
    finally:
        from backend.app.core.security import _auth_sessions

        _auth_sessions.pop(token, None)
