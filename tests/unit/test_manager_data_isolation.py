"""Regression tests: per-manager data isolation.

A trip_manager must only see / mutate the rows they created
(``users.created_by`` / ``vehicles.created_by``) — never another manager's:

* GET  /api/v1/drivers            -> scoped to the calling manager's drivers
* PUT  /api/v1/drivers/{uid}      -> 404 for a driver created by another manager
* POST /api/v1/drivers/{uid}/toggle -> 404 cross-manager
* PUT  /api/v1/vehicles/{vid}     -> 404 cross-manager (visibility clause)
* POST /api/v1/vehicles/{vid}/toggle -> 404 cross-manager
* POST /api/v1/trips              -> 403 when dispatching another manager's driver

super_admin keeps unrestricted access (sees all, edits any).
"""

from __future__ import annotations

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

MOCK_ADMIN = {"user_id": 1, "username": "admin", "role": "super_admin"}
MOCK_MANAGER = {"user_id": 7, "username": "mgr", "role": "trip_manager"}
PLATE = "UP32AB1234"  # matches ^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$


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
    """Patch `get_db` per V1 router; returns (_patch_db, _as_user)."""
    import backend.app.core.security as sec
    from backend.app.api.v1 import deps

    def _patch_db(db_obj):
        for _module in (
            "backend.app.api.v1.trips",
            "backend.app.api.v1.users",
            "backend.app.api.v1.vehicles",
        ):
            monkeypatch.setattr(f"{_module}.get_db", lambda: db_obj)

    def _as_user(user):
        monkeypatch.setattr(sec, "get_current_user", lambda request: user)
        monkeypatch.setattr(deps, "get_current_user", lambda request: user)

    return _patch_db, _as_user


# ---- GET /drivers -----------------------------------------------------------


def test_driver_list_scoped_to_manager(client, resolve_db):
    """A manager's driver listing filters on created_by = their own id."""
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchall.return_value = [
        {"id": 3, "full_name": "Own Driver", "password_hash": "x"}
    ]
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.get("/api/v1/drivers")

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == [{"id": 3, "full_name": "Own Driver"}]
    scoped = [c for c in cur.execute.call_args_list if "FROM users" in str(c.args[0])]
    assert len(scoped) == 1
    assert "created_by = %s" in scoped[0].args[0]
    assert scoped[0].args[1] == (7,), scoped[0].args


def test_driver_list_unscoped_for_super_admin(client, resolve_db):
    """super_admin keeps the unfiltered driver listing."""
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchall.return_value = []
    patch_db(_make_db(cur))
    as_user(MOCK_ADMIN)

    resp = client.get("/api/v1/drivers")

    assert resp.status_code == 200, resp.text
    stmt = str(cur.execute.call_args_list[0].args[0])
    assert "created_by" not in stmt


# ---- Driver mutation ownership ----------------------------------------------


def test_manager_cannot_update_foreign_driver(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchone.return_value = {
        "id": 9, "role": "driver", "created_by": 8,  # owned by manager #8
    }
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.put(
        "/api/v1/drivers/9",
        json={"full_name": "Renamed", "batta_type": "DAILY"},
    )

    assert resp.status_code == 404, resp.text
    assert not any("UPDATE users" in str(c.args[0]) for c in cur.execute.call_args_list)


def test_manager_can_update_own_driver(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchone.return_value = {"id": 5, "role": "driver", "created_by": 7}
    cur.rowcount = 1
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.put(
        "/api/v1/drivers/5",
        json={"full_name": "Renamed", "batta_type": "DAILY", "default_batta_rate": 300},
    )

    assert resp.status_code == 200, resp.text
    assert any("UPDATE users" in str(c.args[0]) for c in cur.execute.call_args_list)


def test_manager_cannot_toggle_foreign_driver(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchone.return_value = {"id": 9, "role": "driver", "created_by": 8}
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.post("/api/v1/drivers/9/toggle", json={"activate": False})

    assert resp.status_code == 404, resp.text
    updates = [c for c in cur.execute.call_args_list if "is_active" in str(c.args[0])]
    assert updates == []


def test_super_admin_can_toggle_any_driver(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchone.return_value = {"id": 9, "role": "driver", "created_by": 8}
    cur.rowcount = 1
    patch_db(_make_db(cur))
    as_user(MOCK_ADMIN)

    resp = client.post("/api/v1/drivers/9/toggle", json={"activate": False})

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["is_active"] is False


# ---- Vehicle mutation ownership ---------------------------------------------


def test_manager_cannot_update_foreign_vehicle(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchone.return_value = None  # visibility clause hides the row
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.put("/api/v1/vehicles/12", json={"vehicle_number": PLATE})

    assert resp.status_code == 404, resp.text
    assert not any(
        "UPDATE vehicles" in str(c.args[0]) for c in cur.execute.call_args_list
    )


def test_manager_can_update_own_vehicle(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchone.side_effect = [{"id": 12}, None]  # visible row, then no plate dup
    cur.rowcount = 1
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.put(
        "/api/v1/vehicles/12",
        json={"vehicle_number": PLATE, "make_model": "Tata 407"},
    )

    assert resp.status_code == 200, resp.text
    assert any("UPDATE vehicles" in str(c.args[0]) for c in cur.execute.call_args_list)


def test_manager_cannot_toggle_foreign_vehicle(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchone.return_value = None
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.post("/api/v1/vehicles/12/toggle", json={"activate": False})

    assert resp.status_code == 404, resp.text
    toggles = [
        c for c in cur.execute.call_args_list if "SET is_active" in str(c.args[0])
    ]
    assert toggles == []


# ---- Trip dispatch ownership ------------------------------------------------


def test_manager_cannot_dispatch_foreign_driver(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    # fetchone sequence: user fleet -> active-trip probe -> driver lookup
    cur.fetchone.side_effect = [
        {"fleet_id": 5},
        None,
        {"id": 9, "role": "driver", "created_by": 8},  # another manager's driver
    ]
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.post(
        "/api/v1/trips",
        json={
            "vehicle_no": PLATE,
            "advance_amount": 5000,
            "start_odo": 1200,
            "driver_user_id": 9,
        },
    )

    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "FORBIDDEN"
    assert not any(
        "INSERT INTO trips" in str(c.args[0]) for c in cur.execute.call_args_list
    )
