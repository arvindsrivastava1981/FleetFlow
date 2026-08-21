"""Regression tests: a newly created Trip Manager must be able to register a vehicle.

Root cause this guards against:
  * api_create_user never bound a new trip_manager to a fleet (users.fleet_id
    stayed NULL), so /api/v1/vehicles resolved to the *default* fleet.
  * In seeded/legacy DBs that default fleet sits in TRIAL with no trial clock
    (trial_ends_at NULL), which `get_fleet_entitlement` reports as PAST_DUE — and
    `_vehicle_limit_ok` then returned 402 VEHICLE_LIMIT on every create.

Fix: on manager creation the default fleet id is bound to the user, and if that
fleet is not currently entitled, the 15-day trial is (re)started so the first
vehicle can be registered immediately.
"""

from __future__ import annotations

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

MOCK_ADMIN = {"user_id": 1, "username": "admin", "role": "super_admin"}
MOCK_MANAGER = {"user_id": 7, "username": "mgr", "role": "trip_manager"}


def _make_db(cur):
    """Wrap a fake cursor in a connection + `with`-able db object."""
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
    """Patch `get_db` per V1 router + `get_current_user` to return the admin."""
    import backend.app.core.security as sec
    from backend.app.api.v1 import deps

    monkeypatch.setattr(sec, "get_current_user", lambda request: MOCK_ADMIN)
    monkeypatch.setattr(deps, "get_current_user", lambda request: MOCK_ADMIN)

    def _patch(db_obj):
        for _module in (
            "backend.app.api.v1.trips",
            "backend.app.api.v1.dashboard",
            "backend.app.api.v1.expenses",
            "backend.app.api.v1.users",
            "backend.app.api.v1.vehicles",
            "backend.app.api.v1.fleets",
            "backend.app.api.v1.benchmarks",
            "backend.app.api.v1.billing",
            "backend.app.api.v1.auth",
        ):
            monkeypatch.setattr(f"{_module}.get_db", lambda: db_obj)

    return _patch


def _manager_create_cur():
    """Cursor with realistic results for the manager-create flow.

    fetchone sequence consumed by api_create_user for a trip_manager:
      1. get_default_fleet      -> {"id": 5, ...}
      2. get_fleet_entitlement  -> TRIAL entitlement (not ACTIVE, no trial clock)
      3. is_trial_active        -> row with subscription_status TRIAL
      4. _trial_plan (via start_trial_subscription) -> subscription_plans row
      5. create_user            -> {"id": 99}
      6. get_default_fleet      -> {"id": 5, ...}
      7. get_fleet_email_context -> {"owner_name": "Default Fleet", ...}
      8. get_user_by_id (email) -> {"id": 99, "full_name": "New Manager"}
    Assertions read the executed SQL/params rather than relying on exact counts.
    """
    cur = mock.MagicMock()
    cur.fetchone.side_effect = [
        {"id": 5, "owner_name": "Default Fleet", "subscription_status": "TRIAL",
         "trial_ends_at": None, "vehicle_limit": 1, "plan_code": "TRIAL"},
        {"subscription_status": "TRIAL", "trial_ends_at": None,
         "vehicle_limit": 1, "plan_code": "TRIAL"},
        {"subscription_status": "TRIAL", "trial_ends_at": None},
        {"id": 1, "code": "TRIAL", "vehicle_limit": 1, "price": 0.0},
        {"id": 99},
        {"id": 99, "full_name": "New Manager", "username": "new_mgr"},
        {"id": 5, "owner_name": "Default Fleet", "plan_name": "Trial Pack"},
        {"id": 5, "owner_name": "Default Fleet", "plan_name": "Trial Pack",
         "subscription_status": "TRIAL", "trial_ends_at": None,
         "vehicle_limit": 1, "driver_limit": 1},
    ]
    cur.fetchall.return_value = []
    return cur


def test_create_trip_manager_binds_default_fleet_and_starts_trial(client, resolve_db):
    """The manager's user row gets fleet_id AND a non-entitled fleet gets a trial."""
    import backend.app.api.v1.users as users_mod
    from unittest.mock import patch

    cur = _manager_create_cur()
    db_obj = _make_db(cur)
    resolve_db(db_obj)

    with patch.object(users_mod, "send_manager_onboarding_email_sync"):
        resp = client.post(
            "/api/v1/users",
            json={
                "username": "new_mgr",
                "full_name": "New Manager",
                "role": "trip_manager",
                "password": "pass1234",
                "phone": "+91 90000 00000",
                "email": "manager@example.com",
            },
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["id"] == 99

    calls = cur.execute.call_args_list
    # Fix 1 — the user insert binds the default fleet id (param index 7).
    insert_call = next(c for c in calls if "INSERT INTO users" in str(c.args[0]))
    assert insert_call.args[1][7] == 5, insert_call.args[1]

    # Fix 2 — a non-entitled default fleet triggers the trial (re)start.
    assert any(
        "UPDATE fleets" in str(c.args[0])
        and "subscription_status = 'TRIAL'" in str(c.args[0])
        for c in calls
    )


def test_create_driver_is_not_bound_to_fleet(client, resolve_db):
    """Drivers are NOT auto-bound to the default fleet (only managers are)."""
    cur = mock.MagicMock()
    cur.fetchone.side_effect = [{"id": 99}]  # create_user -> new id
    cur.fetchall.return_value = []
    db_obj = _make_db(cur)
    resolve_db(db_obj)

    resp = client.post(
        "/api/v1/users",
        json={
            "username": "driver1",
            "full_name": "A Driver",
            "role": "driver",
            "password": "pass1234",
        },
    )

    assert resp.status_code == 200, resp.text
    insert_call = next(
        c for c in cur.execute.call_args_list if "INSERT INTO users" in str(c.args[0])
    )
    # Driver stays unbound (fleet_id None at index 7).
    assert insert_call.args[1][7] is None, insert_call.args[1]


def test_manager_reads_own_fleet(client, resolve_db):
    """A trip_manager can open the Fleets page and sees only their own fleet.

    GET /api/v1/fleets is now scoped for trip_managers: it returns the single
    fleet bound to the caller (users.fleet_id), never the full list.
    """
    import backend.app.core.security as sec
    import backend.app.api.v1.deps as deps

    # Patch identity to a trip_manager for this request.
    sec_patcher = mock.patch.object(
        sec, "get_current_user", lambda request: MOCK_MANAGER
    )
    deps_patcher = mock.patch.object(
        deps, "get_current_user", lambda request: MOCK_MANAGER
    )
    cur = mock.MagicMock()
    cur.fetchone.return_value = {"fleet_id": 12}
    cur.fetchall.return_value = [{"id": 12, "owner_name": "My Fleet", "plan_name": "Trial Pack"}]
    db_obj = _make_db(cur)
    resolve_db(db_obj)

    sec_patcher.start()
    deps_patcher.start()
    try:
        resp = client.get("/api/v1/fleets")
    finally:
        sec_patcher.stop()
        deps_patcher.stop()

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == 12
    # The query was restricted to the caller's fleet id.
    fleet_select = next(
        c for c in cur.execute.call_args_list if "SELECT f.*, sp.name" in str(c.args[0])
    )
    assert fleet_select.args[1] == [12], fleet_select.args[1]


def test_manager_creates_fleet_and_rebinds(client, resolve_db):
    """A trip_manager can create a fleet, and it becomes their active fleet.

    create-fleet is no longer Super-Admin only. After insert_fleet, the
    manager's users.fleet_id is re-pointed to the new fleet so a subsequent
    vehicle creation resolves into it. Toggle/update stay Super-Admin-only.
    """
    import backend.app.core.security as sec
    import backend.app.api.v1.deps as deps

    sec_patcher = mock.patch.object(
        sec, "get_current_user", lambda request: MOCK_MANAGER
    )
    deps_patcher = mock.patch.object(
        deps, "get_current_user", lambda request: MOCK_MANAGER
    )

    cur = mock.MagicMock()
    cur.fetchone.side_effect = [None, {"id": 1, "code": "TRIAL", "vehicle_limit": 1, "price": 0.0}, {"id": 50}]
    # fleet_phone_exists -> None (no dup); _trial_plan -> plan row; insert_fleet -> {"id": 50}
    cur.fetchall.return_value = []
    cur.rowcount = 1
    db_obj = _make_db(cur)
    resolve_db(db_obj)

    sec_patcher.start()
    deps_patcher.start()
    try:
        resp = client.post(
            "/api/v1/fleets",
            json={"owner_name": "X", "phone": "+91 11111 11111", "subscription_plan": "MONTHLY"},
        )
    finally:
        sec_patcher.stop()
        deps_patcher.stop()

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["id"] == 50

    calls = cur.execute.call_args_list
    # Re-bind: users.fleet_id set to the new fleet (id 50).
    rebind = next(
        c for c in calls
        if "UPDATE users" in str(c.args[0]) and "fleet_id" in str(c.args[0])
    )
    assert rebind.args[1][0] == 50, rebind.args[1]


def test_manager_cannot_toggle_fleet(client, resolve_db):
    """Fleet toggle/update remain Super-Admin only (403 for a manager)."""
    import backend.app.core.security as sec
    import backend.app.api.v1.deps as deps

    sec_patcher = mock.patch.object(
        sec, "get_current_user", lambda request: MOCK_MANAGER
    )
    deps_patcher = mock.patch.object(
        deps, "get_current_user", lambda request: MOCK_MANAGER
    )
    db_obj = _make_db(mock.MagicMock())
    resolve_db(db_obj)

    sec_patcher.start()
    deps_patcher.start()
    try:
        resp = client.post("/api/v1/fleets/50/toggle", json={"activate": False})
    finally:
        sec_patcher.stop()
        deps_patcher.stop()

    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "FORBIDDEN"