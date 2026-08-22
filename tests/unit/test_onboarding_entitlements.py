"""Tests for the onboarding/entitlement upgrades.

Covers:
  * `fleet_id` fleet picker when a Super Admin creates a Trip Manager (G1).
  * vehicle-creation gate now distinguishes NOT_ENTITLED from VEHICLE_LIMIT (G3).
"""

from __future__ import annotations

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

MOCK_ADMIN = {"user_id": 1, "username": "admin", "role": "super_admin"}


def _make_db(cur):
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    db_obj = mock.MagicMock()
    db_obj.__enter__ = mock.MagicMock(return_value=conn)
    db_obj.__exit__ = mock.MagicMock(return_value=False)
    return db_obj


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def resolve_db(monkeypatch):
    import backend.app.core.security as sec
    from backend.app.api.v1 import deps

    monkeypatch.setattr(sec, "get_current_user", lambda request: MOCK_ADMIN)
    monkeypatch.setattr(deps, "get_current_user", lambda request: MOCK_ADMIN)

    def _patch(db_obj):
        for _module in (
            "backend.app.api.v1.users",
            "backend.app.api.v1.vehicles",
            "backend.app.api.v1.fleets",
            "backend.app.api.v1.onboard",
            "backend.app.api.v1.trips",
            "backend.app.api.v1.billing",
        ):
            monkeypatch.setattr(f"{_module}.get_db", lambda: db_obj)

    return _patch


def test_create_trip_manager_uses_requested_fleet(client, resolve_db):
    """A Super Admin can target a non-default fleet when creating a manager."""
    from unittest.mock import patch

    import backend.app.api.v1.users as users_mod

    cur = mock.MagicMock()
    # Order: get_fleet_by_id (validate) -> get_fleet_entitlement -> create_user
    #        -> get_user_by_id (onboarding email context)
    cur.fetchone.side_effect = [
        {"id": 42},  # get_fleet_by_id(42)
        {"id": 42, "subscription_status": "ACTIVE", "vehicle_limit": 1,
         "plan_code": "MONTHLY"},  # get_fleet_entitlement (ACTIVE -> short-circuits)
        {"id": 99},  # create_user
        {"id": 99, "full_name": "M"},  # get_user_by_id for onboarding
    ]
    cur.fetchall.return_value = []
    db_obj = _make_db(cur)
    resolve_db(db_obj)

    with patch.object(users_mod, "send_manager_onboarding_email_sync"):
        resp = client.post(
            "/api/v1/users",
            json={
                "username": "m2",
                "full_name": "Manager Two",
                "role": "trip_manager",
                "password": "pass1234",
                "fleet_id": 42,
            },
        )

    assert resp.status_code == 200, resp.text
    insert_call = next(
        c for c in cur.execute.call_args_list if "INSERT INTO users" in str(c.args[0])
    )
    # fleet_id param (index 7) is the requested 42, not the default 5.
    assert insert_call.args[1][7] == 42, insert_call.args[1]


def test_vehicle_gate_reports_not_entitled(client, resolve_db):
    """An un-entitled fleet yields code NOT_ENTITLED, not VEHICLE_LIMIT."""
    cur = mock.MagicMock()
    # vehicle_number_exists (None) -> get_user_fleet_id -> get_fleet_entitlement
    cur.fetchone.side_effect = [
        None,  # vehicle_number_exists -> not present
        {"fleet_id": 7},  # get_user_fleet_id
        {"subscription_status": "PAST_DUE", "trial_ends_at": None,
         "vehicle_limit": 1, "plan_code": "MONTHLY"},  # get_fleet_entitlement
    ]
    cur.fetchall.return_value = []
    db_obj = _make_db(cur)
    resolve_db(db_obj)

    resp = client.post(
        "/api/v1/vehicles",
        json={"vehicle_number": "UP32TA1234", "make_model": "Tata"},
    )

    assert resp.status_code == 402, resp.text
    assert resp.json()["code"] == "NOT_ENTITLED", resp.json()
