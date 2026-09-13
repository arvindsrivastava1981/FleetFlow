"""Regression tests for the trip-manager bug audit (2026-09)."""

from __future__ import annotations

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

MOCK_MANAGER = {"user_id": 7, "username": "mgr", "role": "trip_manager"}
MOCK_ADMIN = {"user_id": 1, "username": "admin", "role": "super_admin"}
PLATE = "UP32AB1234"


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
    def _patch(db_obj, user=MOCK_ADMIN):
        for _module in (
            "backend.app.api.v1.trips",
            "backend.app.api.v1.dashboard",
            "backend.app.api.v1.expenses",
            "backend.app.api.v1.users",
            "backend.app.api.v1.vehicles",
        ):
            monkeypatch.setattr(f"{_module}.get_db", lambda: db_obj)
        monkeypatch.setattr(
            "backend.app.core.security.get_current_user", lambda request: user
        )
        monkeypatch.setattr(
            "backend.app.api.v1.deps.get_current_user", lambda request: user
        )

    return _patch


def test_create_trip_accepts_zero_advance(client, resolve_db):
    """A Rs 0 advance (the NewTrip.jsx default) must create, skipping the
    CASH_ADVANCE ledger leg."""
    cur = mock.MagicMock()
    cur.fetchone.side_effect = [
        {"fleet_id": 5},
        None,
        {"id": 9, "role": "driver", "created_by": 7},
        {"batta_type": "FIXED_TRIP", "default_batta_rate": 500},
        None,
        {"id": 77},
        {"id": 78},
    ]
    cur.fetchall.return_value = []
    resolve_db(_make_db(cur), user=MOCK_MANAGER)
    resp = client.post(
        "/api/v1/trips",
        json={"vehicle_no": PLATE, "advance_amount": 0,
              "start_odo": 1200, "driver_user_id": 9},
    )
    assert resp.status_code in (200, 201), resp.text
    inserts = [str(c.args[0]) for c in cur.execute.call_args_list]
    assert any("INSERT INTO trips" in s for s in inserts)
    cash = [c for c in cur.execute.call_args_list
            if "INSERT INTO expenses" in str(c.args[0])]
    kinds = [c.args[1][2] for c in cash]
    assert kinds == ["DRIVER_SALARY"], kinds


def test_create_trip_still_rejects_negative_advance(client, resolve_db):
    """Negative advances stay invalid; the route must not touch the DB."""
    cur = mock.MagicMock()
    resolve_db(_make_db(cur), user=MOCK_MANAGER)
    resp = client.post(
        "/api/v1/trips",
        json={"vehicle_no": PLATE, "advance_amount": -100,
              "start_odo": 1200, "driver_user_id": 9},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "INVALID_ADVANCE"
    assert cur.execute.call_args_list == []


def test_trip_stats_query_is_scoped_to_page():
    """Stats aggregate filters on the page trip codes, not a full scan."""
    from backend.app.db.queries import trips as trip_queries
    conn = mock.MagicMock()
    cur = mock.MagicMock()
    conn.cursor.return_value = cur
    cur.fetchall.return_value = []
    trip_queries.get_trip_stats_by_code(conn, ["1234-1", "1234-2"])
    stmt = str(cur.execute.call_args.args[0])
    params = cur.execute.call_args.args[1]
    assert "WHERE trip_code = ANY(%s)" in stmt
    assert params == (["1234-1", "1234-2"],)


def test_trip_stats_empty_page_skips_query():
    """An empty page must not hit the DB at all."""
    from backend.app.db.queries import trips as trip_queries
    conn = mock.MagicMock()
    assert trip_queries.get_trip_stats_by_code(conn, []) == {}
    conn.cursor.assert_not_called()


def test_trip_list_route_passes_page_codes_to_stats(client, resolve_db, monkeypatch):
    """GET /trips wires the page trip_codes into the scoped stats query."""
    from backend.app.api.v1 import trips as trips_route
    seen = {}

    def _fake_stats(conn, trip_codes=None):
        seen["codes"] = list(trip_codes or [])
        return {}

    monkeypatch.setattr(trips_route, "get_trip_stats_by_code", _fake_stats)
    cur = mock.MagicMock()
    cur.fetchall.return_value = [{"trip_code": "1234-1", "status": "ACTIVE", "id": 1}]
    resolve_db(_make_db(cur), user=MOCK_ADMIN)
    resp = client.get("/api/v1/trips")
    assert resp.status_code == 200, resp.text
    assert seen["codes"] == ["1234-1"]


def test_same_fleet_manager_can_read_trip():
    """Same-fleet manager passes the tenant check without being the creator."""
    from backend.app.api.v1.deps import _trip_forbidden
    conn = mock.MagicMock()
    cur = mock.MagicMock()
    conn.cursor.return_value = cur
    cur.fetchone.return_value = {"fleet_id": 5}
    trip = {"created_by": 7, "driver_user_id": 9, "fleet_id": 5}
    assert _trip_forbidden(conn, {"user_id": 8, "role": "trip_manager"}, trip) is False


def test_cross_fleet_manager_still_forbidden():
    """A manager from another fleet must still be denied."""
    from backend.app.api.v1.deps import _trip_forbidden
    conn = mock.MagicMock()
    cur = mock.MagicMock()
    conn.cursor.return_value = cur
    cur.fetchone.return_value = {"fleet_id": 6}
    trip = {"created_by": 8, "driver_user_id": 9, "fleet_id": 5}
    assert _trip_forbidden(conn, {"user_id": 8, "role": "trip_manager"}, trip) is True
