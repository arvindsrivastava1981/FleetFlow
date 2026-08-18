"""Unit tests for the settlement payload on `GET /api/v1/trips/{trip_code}`.

Verifies that the `settlement` object attached to the trip detail response
strictly mirrors the single-source `compute_settlement()` engine, and that the
FULLY SETTLED / refund-direction status logic matches it. No live Neon DB is
touched — the DB cursor chain and auth identity are mocked.
"""
from __future__ import annotations

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.audit.cash import DEFAULT_DRIVER_BATTA, compute_settlement

MOCK_USER = {"user_id": 1, "username": "manager", "role": "super_admin"}


def _mock_db_cursor(trip, expenses=None):
    """Build a fake cursor+connection that yields the trip and expense rows."""
    expenses = expenses or []
    cur = mock.MagicMock()
    cur.fetchone.side_effect = [trip]
    cur.fetchall.return_value = expenses
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    db_obj = mock.MagicMock()
    db_obj.__enter__ = mock.MagicMock(return_value=conn)
    db_obj.__exit__ = mock.MagicMock(return_value=False)
    return db_obj


def _mock_multi_cursor(*fetchone_values, fetchall_value=None):
    """Fake cursor whose successive fetchone calls return each value."""
    cur = mock.MagicMock()
    cur.fetchone.side_effect = list(fetchone_values)
    cur.fetchall.return_value = fetchall_value or []
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    db_obj = mock.MagicMock()
    db_obj.__enter__ = mock.MagicMock(return_value=conn)
    db_obj.__exit__ = mock.MagicMock(return_value=False)
    return db_obj


def _exp(exp_type="FUEL", amount=100.0, approved_amount=None,
         manager_status="APPROVED", liters=10.0) -> dict:
    return {
        "exp_type": exp_type,
        "amount": amount,
        "approved_amount": approved_amount,
        "liters": liters,
        "manager_status": manager_status,
        "is_flagged": False,
        "odometer": 1000.0,
        "rate": 90.50,
    }


def _trip(**kw) -> dict:
    base = {
        "id": 1,
        "trip_code": "TRIP-101",
        "vehicle_no": "MH12AB1234",
        "vehicle_id": None,
        "driver_name": "Ramesh",
        "driver_phone": "+919876543210",
        "driver_user_id": None,
        "advance_amount": 10000.0,
        "start_odo": 100000.0,
        "end_odo": None,
        "current_odo": 100500.0,
        "status": "ACTIVE",
        "origin": "Pune",
        "destination": "Mumbai",
        "driver_batta_amount": DEFAULT_DRIVER_BATTA,
        "verification_hash": None,
        "created_by": 1,
        "fleet_id": 1,
    }
    base.update(kw)
    return base


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def resolve_db(monkeypatch):
    """Patch `get_db` and `get_current_user`; return a function to (re)set them.

    The route calls get_db() as a context manager and fetchone/fetchall against
    its cursor. Provide fresh MagicMocks per test via closure.
    """

    def _patch(db_obj, user=MOCK_USER):
        monkeypatch.setattr("backend.app.api.api_v1.get_db", lambda: db_obj)
        # require_json_auth / require_json_role call core.security.get_current_user;
        # api_v1._identity uses api_v1's own imported reference. Patch both.
        monkeypatch.setattr(
            "backend.app.core.security.get_current_user", lambda request: user
        )
        monkeypatch.setattr(
            "backend.app.api.api_v1.get_current_user", lambda request: user
        )

    return _patch


def test_trip_detail_settlement_mirrors_compute_settlement(client, resolve_db):
    """The API settlement dict equals the engine's result for the same input."""
    expenses = [
        _exp(exp_type="GOODS_SALE", amount=30000.0),
        _exp(exp_type="FUEL", amount=5000.0, liters=50.0),
        _exp(exp_type="REPAIR", amount=2000.0, approved_amount=1500.0),
        _exp(exp_type="CHALLAN", amount=1000.0),
    ]
    trip = _trip(advance_amount=20000.0)
    expected = compute_settlement(trip, expenses)

    resolve_db(_mock_db_cursor(trip, expenses))
    resp = client.get("/api/v1/trips/TRIP-101")

    assert resp.status_code == 200
    s = resp.json()["data"]["trip"]["settlement"]

    assert s["advance_amount"] == expected.advance_amount
    assert s["goods_income"] == expected.goods_income
    assert s["total_cr"] == expected.total_cr
    assert s["total_road_expenses"] == expected.total_road_expenses
    assert s["driver_batta"] == expected.driver_batta
    assert s["total_driver_credits"] == expected.total_driver_credits
    assert s["net_balance"] == expected.net_balance
    assert s["is_driver_refund"] == expected.is_driver_refund
    assert s["status_label_en"] == expected.status_label_en
    assert s["status_label_hi"] == expected.status_label_hi
    assert s["verification_hash"] == expected.verification_hash
    assert s["avg_kml"] == expected.avg_kml
    assert s["expense_buckets"] == expected.expense_buckets

    # Cross-check the two headline numbers directly against the formula.
    assert s["net_balance"] == pytest.approx(20000.0 + 30000.0 - (5000.0 + 1500.0 + 1000.0 + 2500.0))
    assert s["total_driver_credits"] == pytest.approx(5000.0 + 1500.0 + 1000.0 + 2500.0)


def test_trip_detail_fully_settled_when_net_zero(client, resolve_db):
    """net_balance == 0 produces status FULLY SETTLED and no refund direction."""
    expenses = [_exp(exp_type="FUEL", amount=2500.0, liters=25.0)]
    trip = _trip(advance_amount=5000.0)

    resolve_db(_mock_db_cursor(trip, expenses))
    resp = client.get("/api/v1/trips/TRIP-101")

    assert resp.status_code == 200
    s = resp.json()["data"]["trip"]["settlement"]
    assert s["net_balance"] == 0.0
    assert s["status_label_en"] == "FULLY SETTLED"
    assert s["is_driver_refund"] is False


def test_driver_overview_cash_in_hand_subtracts_batta(client, resolve_db):
    """Driver cash-in-hand = advance + approved net - driver batta."""
    trip = _trip(advance_amount=10000.0, driver_user_id=2)
    # fetchone sequence: get_active_trip_for_driver -> trip dict;
    # driver_today_logged -> {"total": ...}; approved_cash_net -> {"net": ...}.
    db_obj = _mock_multi_cursor(
        trip, {"total": 0.0}, {"net": -2000.0},
    )
    driver_user = {"user_id": 2, "username": "driver", "role": "driver"}
    resolve_db(db_obj, user=driver_user)

    resp = client.get("/api/v1/dashboard/overview")

    assert resp.status_code == 200
    body = resp.json()["data"]
    # advance 10000 + (-2000) - batta 2500
    assert body["cash_in_hand"] == pytest.approx(10000.0 - 2000.0 - DEFAULT_DRIVER_BATTA)


def test_trip_detail_returns_404_for_unknown_trip(client, resolve_db):
    """An unknown trip yields 404 before any settlement math."""
    db_obj = _mock_db_cursor(trip=None)

    resolve_db(db_obj)
    resp = client.get("/api/v1/trips/NOPE")

    assert resp.status_code == 404


def test_json_mutation_parses_dict_not_coroutine(client, resolve_db):
    """JSON mutations must await request.json(); otherwise the body is a
    coroutine and every save returns 'body must be a JSON object'.

    Regression for the Starlette >= 0.20 change where `Request.json` became
    async: sync handlers calling `request.json()` without `await` produce a
    coroutine object, so `isinstance(body, dict)` is always False and the
    update/create endpoints reject valid payloads.
    """
    cur = mock.MagicMock()
    # update_user -> fetchone (existence) / execute; settle unaffected here.
    cur.fetchone.return_value = {"id": 1}
    cur.fetchall.return_value = []
    cur.rowcount = 1
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    db_obj = mock.MagicMock()
    db_obj.__enter__ = mock.MagicMock(return_value=conn)
    db_obj.__exit__ = mock.MagicMock(return_value=False)

    resolve_db(db_obj, user={"user_id": 1, "username": "admin", "role": "super_admin"})

    resp = client.put(
        "/api/v1/users/1",
        json={"username": "x", "full_name": "X", "role": "trip_manager"},
    )

    # The body must be read as a dict — not rejected as "body must be a JSON object".
    assert resp.status_code == 200
    assert "body must be a JSON object" not in resp.text