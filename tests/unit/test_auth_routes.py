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
    "trip_code": "TRIP-TEST",
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


def test_unauthenticated_reset_demo_redirects_to_login():
    # The original CRITICAL: `/reset-demo` wiped all data via any GET.
    assert_login_redirect(client.get("/reset-demo"))


def test_healthz_public():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_form_is_public():
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "Login" in resp.text