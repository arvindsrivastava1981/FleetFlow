"""Tests for the transactional onboarding wizard (`POST /api/v1/fleets/onboard`).

Covers:
  * full onboarding in one request: fleet + owner Trip Manager + TRIAL + optional
    first vehicle + optional first driver.
  * the owner welcome email is dispatched on the onboard path (matches Path A).
  * manager-only onboarding (both vehicle and driver omitted) — clean 200.
  * a duplicate fleet phone is rejected (409 DUP_PHONE).
  * a missing owner (manager) aborts with 400 MISSING_FIELDS before any insert.
"""

from __future__ import annotations

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

MOCK_ADMIN = {"user_id": 1, "username": "admin", "role": "super_admin"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_session(monkeypatch):
    """Patch `get_current_user` for both security + deps so we act as Super Admin."""
    import backend.app.core.security as sec
    from backend.app.api.v1 import deps

    monkeypatch.setattr(sec, "get_current_user", lambda request: MOCK_ADMIN)
    monkeypatch.setattr(deps, "get_current_user", lambda request: MOCK_ADMIN)


def _make_db(cur):
    """Wrap a fake cursor in a `with`-able db object + connection."""
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    db_obj = mock.MagicMock()
    db_obj.__enter__ = mock.MagicMock(return_value=conn)
    db_obj.__exit__ = mock.MagicMock(return_value=False)
    return db_obj


@pytest.fixture
def onboard_db(monkeypatch):
    """Stub the db/email dependency surface of the onboard module."""
    import backend.app.api.v1.onboard as onboard
    import backend.app.services.entitlements as entitlements

    monkeypatch.setattr(onboard, "get_db", lambda: _make_db(mock.MagicMock()))
    monkeypatch.setattr(onboard, "fleet_phone_exists", lambda conn, phone: False)
    monkeypatch.setattr(onboard, "vehicle_number_exists", lambda conn, num: False)
    monkeypatch.setattr(onboard, "get_fleet_entitlement", lambda conn, fid: {})
    monkeypatch.setattr(entitlements, "fleet_can_add_vehicles", lambda conn, fid, ent: (True, None))
    monkeypatch.setattr(onboard, "insert_vehicle", lambda *a, **kw: 4)
    monkeypatch.setattr(onboard, "start_trial_subscription", lambda conn, fid: None)
    monkeypatch.setattr(onboard, "log_fleet_billing_event", lambda *a, **kw: None)

    def _insert_fleet(conn, owner_name, phone, email=None, **kw):
        return 1

    monkeypatch.setattr(onboard, "insert_fleet", _insert_fleet)

    fleet_row = {
        "id": 1, "owner_name": "Arvind Srivastava", "email": "billing@arvind.example",
        "subscription_status": "TRIAL", "vehicle_limit": 1, "driver_limit": 1,
        "trial_ends_at": None, "next_billing_date": None,
        "plan_name": "Trial Pack", "default_batta_rate": None,
    }
    monkeypatch.setattr(onboard, "get_fleet_email_context", lambda conn, fid: fleet_row)

    calls = {}
    monkeypatch.setattr(
        onboard, "send_manager_onboarding_email_sync",
        lambda **kw: calls.update(kw) or {"status": "queued", "queued": True},
    )
    return {"fleet_row": fleet_row, "email_calls": calls}


def _full_payload() -> dict:
    return {
        "fleet": {
            "owner_name": "Arvind Srivastava",
            "phone": "+91 99999 00000",
            "email": "billing@arvind.example",
        },
        "owner": {
            "username": "arvind",
            "full_name": "Arvind Srivastava",
            "password": "Temp#12345",
            "email": "arvind@example.com",
        },
        "plan_code": "TRIAL",
        "initial_vehicle": {
            "vehicle_number": "UP32TA1234",
            "make_model": "Tata 407",
            "tank_capacity_liters": 350.0,
            "expected_km_per_liter": 4.0,
        },
        "initial_driver": {
            "username": "raju",
            "full_name": "Raju Driver",
            "password": "Driver#123",
            "phone": "+91 88888 77777",
            "batta_type": "PER_KM",
            "default_batta_rate": 12.0,
        },
    }


def test_onboard_full_with_email(client, admin_session, onboard_db):
    """A full onboard creates fleet+manager+vehicle+driver and emails the manager."""
    email_calls = onboard_db["email_calls"]
    import backend.app.api.v1.onboard as onboard

    seq = iter([2, 3])  # owner id, driver id
    onboard.create_user = lambda conn, *a, **kw: next(seq)

    resp = client.post("/api/v1/fleets/onboard", json=_full_payload())
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["fleet_id"] == 1
    assert data["owner_user_id"] == 2
    assert data["vehicle_id"] == 4
    assert data["driver_user_id"] == 3
    assert data["plan_code"] == "TRIAL"
    assert data["email_queued"] is True
    # Welcome email carried the owner's email + temporary password.
    assert email_calls["to_email"] == "arvind@example.com"
    assert email_calls["temporary_password"] == "Temp#12345"
    assert email_calls["username"] == "arvind"


def test_onboard_manager_only_without_vehicle_or_driver(client, admin_session, onboard_db):
    """Omitting vehicle + driver is valid — firm + manager alone succeeds."""
    import backend.app.api.v1.onboard as onboard

    onboard.create_user = lambda conn, *a, **kw: 2
    payload = {
        "fleet": {"owner_name": "Mini Fleet", "phone": "+91 99999 11111", "email": "mini@example.com"},
        "owner": {"username": "mini", "full_name": "Mini Owner", "password": "Mini#12345", "email": "mini@example.com"},
        "plan_code": "TRIAL",
    }
    resp = client.post("/api/v1/fleets/onboard", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["fleet_id"] == 1
    assert data["owner_user_id"] == 2
    assert data["vehicle_id"] is None
    assert data["driver_user_id"] is None
    assert data["email_queued"] is True


def test_onboard_duplicate_fleet_phone(client, admin_session, onboard_db):
    """A duplicate fleet phone yields 409 DUP_PHONE and nothing is created."""
    import backend.app.api.v1.onboard as onboard

    onboard.fleet_phone_exists = lambda conn, phone: True
    resp = client.post("/api/v1/fleets/onboard", json=_full_payload())
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "DUP_PHONE"


def test_onboard_missing_owner_aborts(client, admin_session, onboard_db):
    """Without the owner/manager the wizard rejects before any insert."""
    payload = {
        "fleet": {"owner_name": "Solo", "phone": "+91 99999 22222"},
        "owner": {"username": "", "full_name": "", "password": ""},
        "plan_code": "TRIAL",
    }
    resp = client.post("/api/v1/fleets/onboard", json=payload)
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "MISSING_FIELDS"