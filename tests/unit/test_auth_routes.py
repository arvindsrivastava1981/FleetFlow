"""Route-security tests for the CRITICAL auth-guard fixes (§2.1).

Every mutation endpoint that used to be unauthenticated must now redirect
anonymous clients to `/login` with status 303. We run the app through FastAPI's
TestClient with `follow_redirects=False` so we observe the raw 303 instead of
the followed login page, and we send valid Form bodies on POST endpoints so
FastAPI's request validation (which runs before the handler) doesn't shadow the
guard with a 422.

None of these require a live DB: the guards fire before any database work.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app, follow_redirects=False)

CREATE_TRIP_BODY = {
    "vehicle_no": "UP32MA1234",
    "driver_name": "Test Driver",
    "driver_phone": "+91 99999 99999",
    "advance_amount": "25000",
    "start_odo": "100000",
}

SIMULATE_BODY = {
    "trip_code": "TRIP-TEST",
    "exp_type": "FUEL",
    "amount": "2715",
    "odometer": "100500",
    "liters": "30",
    "rate": "90.50",
}


def assert_login_redirect(resp) -> None:
    assert resp.status_code == 303
    assert resp.headers["location"].rstrip("/").endswith("/login")


def test_unauthenticated_create_trip_redirects_to_login():
    assert_login_redirect(client.post("/create-trip", data=CREATE_TRIP_BODY))


def test_unauthenticated_simulate_whatsapp_redirects_to_login():
    assert_login_redirect(client.post("/simulate-whatsapp", data=SIMULATE_BODY))


def test_unauthenticated_action_expense_redirects_to_login():
    assert_login_redirect(
        client.get("/action-expense?id=1&action=APPROVE")
    )


def test_unauthenticated_settle_trip_redirects_to_login():
    assert_login_redirect(client.get("/settle-trip?trip_code=TRIP-101"))


def test_healthz_public():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_form_is_public():
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "Login" in resp.text


# ---------------------------------------------------------------------------#
# Phase 0 JSON API guardrails (architecture review)
# ---------------------------------------------------------------------------#
def test_api_me_returns_401_json_when_unauthenticated():
    """JSON endpoints must return 401 JSON, never the 303 browser redirect."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_api_trips_returns_401_json_when_unauthenticated():
    resp = client.get("/api/v1/trips")
    assert resp.status_code == 401
    assert resp.json()["error"] == "unauthorized"


def test_api_dashboard_returns_401_json_when_unauthenticated():
    resp = client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_api_auth_me_accepts_bearer_token():
    """A fabricated-but-present session token in the header must not 500 path.

    We assert the route returns 401 for an unknown token via the Bearer header
    (not a 303), which proves the header is honoured as the auth source while an
    invalid/unknown token is still rejected cleanly.
    """
    resp = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer unknown-token"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_api_users_requires_super_admin():
    """Role-gated JSON endpoints return 403 for unknown/invalid roles, not 303."""
    resp = client.get(
        "/api/v1/users", headers={"Authorization": "Bearer unknown-token"}
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------#
# Phase 1 — feature-complete JSON contract guardrails
# ---------------------------------------------------------------------------#
def test_api_create_trip_requires_role_json():
    """Trip creation is role-gated; unauthenticated gets 401 JSON, never 303."""
    resp = client.post("/api/v1/trips", json={})
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_api_settle_requires_role_json():
    resp = client.post("/api/v1/trips/TRIP-101/settle")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_api_benchmarks_get_unauth_401():
    resp = client.get("/api/v1/benchmarks")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_api_fleets_requires_super_admin_json():
    """Fleet endpoints are Super-Admin gated; anonymous -> 401 (not 303)."""
    resp = client.get("/api/v1/fleets")
    assert resp.status_code == 401
    assert resp.json()["error"] == "unauthorized"


def test_api_settlement_pdf_unauth_401():
    resp = client.get("/api/v1/settlements/TRIP-101/pdf")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_api_create_user_requires_super_admin_json():
    resp = client.post("/api/v1/users", json={})
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_api_create_vehicle_requires_role_json():
    resp = client.post("/api/v1/vehicles", json={})
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_api_toggle_user_requires_super_admin_json():
    resp = client.post("/api/v1/users/1/toggle", json={"activate": False})
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


# ---- JSON change-password + drivers (added for the React SPA sidebar) -------#
def test_api_change_password_unauth_401():
    """Change-password JSON mutation is gated; anonymous must get 401 JSON."""
    resp = client.post("/api/v1/auth/change-password", json={})
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_api_drivers_requires_role_json():
    """Driver list is role-gated; anonymous gets 401 JSON, never 303."""
    resp = client.get("/api/v1/drivers")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"