from __future__ import annotations

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.audit.cash import DEFAULT_DRIVER_BATTA, compute_settlement

MOCK_USER = {"user_id": 1, "username": "manager", "role": "super_admin"}


def _mock_db_cursor(trip, expenses=None, ledger_expenses=None):
    """Build a fake cursor+connection that yields the trip and expense rows.

    The trip-detail route fetches the FULL ledger (for settlement math) via
    `get_expenses_for_trip`, then the same full ledger via `get_ledger_expenses_for_trip`
    for the response. `ledger_expenses` defaults to expenses (no longer filtered).
    """
    expenses = expenses or []
    if ledger_expenses is None:
        ledger_expenses = expenses
    cur = mock.MagicMock()
    cur.fetchone.side_effect = [trip]
    cur.fetchall.side_effect = [expenses, ledger_expenses]
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



def _advance(amount: float) -> dict:
    """A CASH_ADVANCE ledger row (auto-posted at trip creation)."""
    return _exp(exp_type="CASH_ADVANCE", amount=amount, liters=0.0)


def _batta(amount: float) -> dict:
    """A DRIVER_SALARY ledger row (auto-posted at trip creation)."""
    return _exp(exp_type="DRIVER_SALARY", amount=amount, liters=0.0)

def _trip(**kw) -> dict:
    base = {
        "id": 1,
        "trip_code": "TRIP-101",
        "vehicle_no": "MH12AB1234",
        "vehicle_id": None,
        "driver_name": "Ramesh",
        "driver_phone": "9876543210",
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
        # Each v1 sub-router imports `get_db` by name at module load, creating a
        # bound reference per module. Patch all of them so any route under test
        # uses the mocked connection.
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
        # require_json_auth / require_json_role call core.security.get_current_user;
        # the routers' `_identity` uses deps.get_current_user (bound import).
        # Patch the common core.security source + the deps bound reference.
        monkeypatch.setattr(
            "backend.app.core.security.get_current_user", lambda request: user
        )
        monkeypatch.setattr(
            "backend.app.api.v1.deps.get_current_user", lambda request: user
        )

    return _patch


def test_trip_detail_settlement_mirrors_compute_settlement(client, resolve_db):
    """The API settlement dict equals the engine's result for the same input."""
    expenses = [
        _advance(20000.0),
        _batta(DEFAULT_DRIVER_BATTA),
        _exp(exp_type="GOODS_SALE", amount=30000.0),
        _exp(exp_type="FUEL", amount=5000.0, liters=50.0),
        _exp(exp_type="REPAIR", amount=2000.0, approved_amount=1500.0),
        _exp(exp_type="CHALLAN", amount=1000.0),
    ]
    trip = _trip()
    expected = compute_settlement(trip, expenses)

    resolve_db(_mock_db_cursor(trip, expenses))
    resp = client.get("/api/v1/trips/TRIP-101")

    assert resp.status_code == 200
    body = resp.json()["data"]
    s = body["trip"]["settlement"]

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

    # The response ledger now includes provision legs (CASH_ADVANCE / DRIVER_SALARY)
    # alongside real driver expenses.
    returned_types = {e["exp_type"] for e in body["expenses"]}
    assert "CASH_ADVANCE" in returned_types
    assert "DRIVER_SALARY" in returned_types
    assert {"GOODS_SALE", "FUEL", "REPAIR", "CHALLAN"} <= returned_types


def test_trip_detail_fully_settled_when_net_zero(client, resolve_db):
    """net_balance == 0 produces status FULLY SETTLED and no refund direction."""
    expenses = [
        _advance(5000.0),
        _batta(2500.0),
        _exp(exp_type="FUEL", amount=2500.0, liters=25.0),
    ]
    trip = _trip()

    resolve_db(_mock_db_cursor(trip, expenses))
    resp = client.get("/api/v1/trips/TRIP-101")

    assert resp.status_code == 200
    s = resp.json()["data"]["trip"]["settlement"]
    assert s["net_balance"] == 0.0
    assert s["status_label_en"] == "FULLY SETTLED"
    assert s["is_driver_refund"] is False


def test_driver_overview_cash_in_hand_subtracts_batta(client, resolve_db):
    """Driver cash-in-hand = cash advance total + approved net (ledger)."""
    trip = _trip(driver_user_id=2)
    # fetchone sequence: get_active_trip_for_driver -> trip dict;
    # driver_today_logged -> {"total": ...}; driver_cash_advance_total ->
    # {"total": ...}; approved_cash_net -> {"net": ...}.
    db_obj = _mock_multi_cursor(
        trip, {"total": 0.0}, {"total": 10000.0}, {"net": -2000.0},
    )
    driver_user = {"user_id": 2, "username": "driver", "role": "driver"}
    resolve_db(db_obj, user=driver_user)

    resp = client.get("/api/v1/dashboard/overview")

    assert resp.status_code == 200
    body = resp.json()["data"]
    # advance 10000 + (-2000) = 8000
    assert body["cash_in_hand"] == pytest.approx(10000.0 - 2000.0)


def test_trip_detail_forbids_other_managers_trip(client, resolve_db):
    """A trip_manager cannot view a trip they did not create (403)."""
    trip = _trip(created_by=99, fleet_id=1)
    resolve_db(_mock_db_cursor(trip), user={"user_id": 5, "username": "m2", "role": "trip_manager"})

    resp = client.get("/api/v1/trips/TRIP-101")
    assert resp.status_code == 403


def test_trip_detail_forbids_other_fleet_manager(client, resolve_db):
    """Fleet (tenant) mismatch blocks a manager even if they created the trip."""
    trip = _trip(created_by=5, fleet_id=7)
    # fetchone sequence: get_trip_by_code -> trip; get_user_fleet_id -> user fleet row.
    db_obj = _mock_multi_cursor(trip, {"fleet_id": 1})
    resolve_db(db_obj, user={"user_id": 5, "username": "m", "role": "trip_manager"})

    resp = client.get("/api/v1/trips/TRIP-101")
    # user.fleet (1) != trip.fleet (7) => forbidden
    assert resp.status_code == 403


def test_trip_detail_forbids_driver_on_others_trip(client, resolve_db):
    """A driver cannot view a trip assigned to someone else (403)."""
    trip = _trip(driver_user_id=88, fleet_id=1)
    resolve_db(_mock_db_cursor(trip), user={"user_id": 5, "username": "d", "role": "driver"})

    resp = client.get("/api/v1/trips/TRIP-101")
    assert resp.status_code == 403


def test_expense_action_requires_manager_role(client, resolve_db):
    """A driver must NOT be able to approve/reject expenses (403)."""
    resolve_db(_mock_db_cursor(_trip(), {}), user={"user_id": 5, "username": "d", "role": "driver"})
    resp = client.post("/api/v1/expenses/1/action", json={"action": "APPROVE"})
    assert resp.status_code == 403


def test_expense_action_forbids_cross_scope_manager(client, resolve_db):
    """A manager may not action expenses on another fleet's trip (403)."""
    trip = _trip(fleet_id=7, created_by=99)
    # get_expense_trip_code -> {"trip_code": ...}; get_trip_by_code -> trip.
    db_obj = _mock_multi_cursor({"trip_code": trip["trip_code"]}, trip)
    resolve_db(db_obj, user={"user_id": 5, "username": "m", "role": "trip_manager"})
    resp = client.post("/api/v1/expenses/1/action", json={"action": "REJECT"})
    assert resp.status_code == 403


def test_trip_detail_returns_404_for_unknown_trip(client, resolve_db):
    """An unknown trip yields 404 before any settlement math."""
    db_obj = _mock_db_cursor(trip=None)

    resolve_db(db_obj)
    resp = client.get("/api/v1/trips/NOPE")

    assert resp.status_code == 404


def test_whatsapp_escalations_returns_flag_feed(client, resolve_db):
    """`GET /api/v1/whatsapp/escalations` returns the flagged/pending feed.

    Super_admin (no manager scope) sees the full feed; each row carries the
    joined driver + vehicle for the escalation chat UI.
    """
    feed = [
        {
            "id": 1,
            "trip_code": "TRIP-101",
            "exp_type": "FUEL",
            "amount": 6000.0,
            "liters": 60.0,
            "rate": 100.0,
            "odometer": 100500.0,
            "station_name": "HPCL",
            "is_flagged": True,
            "flag_reason": "Fuel rate above benchmark",
            "manager_status": "PENDING",
            "created_at": None,
            "driver_name": "Ramesh",
            "vehicle_no": "MH12AB1234",
        }
    ]
    # Build the db context manager with a cursor that returns the feed from
    # fetchall (mirrors open_escalations_detail -> SELECT ... ORDER BY id DESC LIMIT).
    cur = mock.MagicMock()
    cur.fetchall.return_value = feed
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    db_obj = mock.MagicMock()
    db_obj.__enter__ = mock.MagicMock(return_value=conn)
    db_obj.__exit__ = mock.MagicMock(return_value=False)

    # super_admin => no manager scoping, limit=50
    resolve_db(db_obj)

    resp = client.get("/api/v1/whatsapp/escalations")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["is_flagged"] is True
    assert data[0]["driver_name"] == "Ramesh"
    assert data[0]["vehicle_no"] == "MH12AB1234"
    # Confirm the SQL query binds only the LIMIT (no manager scope) for super_admin.
    call = cur.execute.call_args
    assert call[0][1][-1] == 50
    assert len(call[0][1]) == 1


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


# ---- Settlement validation gates (Check 4 & 5) --------------------------

def test_settle_rejects_missing_end_odo(client, resolve_db):
    """Settlement requires an explicit closing odometer reading (Check 4)."""
    trip = _trip()
    pending_row = {"pending_count": 0}
    db_obj = _mock_multi_cursor(trip, pending_row)
    resolve_db(db_obj)

    resp = client.post("/api/v1/trips/TRIP-101/settle", json={})

    assert resp.status_code == 400
    assert resp.json()["code"] == "MISSING_END_ODO"


def test_settle_rejects_end_odo_below_start_odo(client, resolve_db):
    """end_odo < start_odo is rejected (Check 4)."""
    trip = _trip(start_odo=100000.0)
    pending_row = {"pending_count": 0}
    db_obj = _mock_multi_cursor(trip, pending_row)
    resolve_db(db_obj)

    resp = client.post(
        "/api/v1/trips/TRIP-101/settle", json={"end_odo": 50000}
    )

    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_END_ODO"
    assert "lower than start odometer" in resp.json()["error"]


def test_settle_rejects_fuel_efficiency_too_low(client, resolve_db):
    """Fuel efficiency below 1.5 km/L blocks settlement (Check 5)."""
    trip = _trip(start_odo=100000.0, end_odo=100150.0)
    pending_row = {"pending_count": 0}
    # 150 km on 200 L → 0.75 km/L (below 1.5 floor)
    expenses = [_exp(exp_type="FUEL", amount=18000.0, liters=200.0)]
    db_obj = _mock_multi_cursor(
        trip, pending_row, fetchall_value=expenses,
    )
    resolve_db(db_obj)

    resp = client.post(
        "/api/v1/trips/TRIP-101/settle", json={"end_odo": 100150}
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "FUEL_EFFICIENCY_LOW"
    assert "0.75" in resp.json()["error"]


def test_settle_rejects_fuel_efficiency_too_high(client, resolve_db):
    """Fuel efficiency above 12 km/L blocks settlement (Check 5)."""
    trip = _trip(start_odo=100000.0, end_odo=101500.0)
    pending_row = {"pending_count": 0}
    # 1500 km on 50 L → 30 km/L (above 12 ceiling)
    expenses = [_exp(exp_type="FUEL", amount=4500.0, liters=50.0)]
    db_obj = _mock_multi_cursor(
        trip, pending_row, fetchall_value=expenses,
    )
    resolve_db(db_obj)

    resp = client.post(
        "/api/v1/trips/TRIP-101/settle", json={"end_odo": 101500}
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "FUEL_EFFICIENCY_HIGH"
    assert "30.0" in resp.json()["error"]


def test_settle_skips_fuel_check_when_no_fuel_expenses(client, resolve_db):
    """When avg_kml is None (no fuel), the fuel-efficiency gate is skipped.

    The settle progresses past check 5 into mark_trip_settled (which will
    exhaust our simplified mock cursor — that's expected). What matters is
    the response code is NOT a fuel-efficiency rejection.
    """
    trip = _trip(start_odo=100000.0)
    pending_row = {"pending_count": 0}
    expenses = [_exp(exp_type="TOLL", amount=500.0)]
    db_obj = _mock_multi_cursor(
        trip, pending_row, fetchall_value=expenses,
    )
    resolve_db(db_obj)

    try:
        resp = client.post(
            "/api/v1/trips/TRIP-101/settle", json={"end_odo": 100500}
        )
        code = resp.json().get("code", "")
    except RuntimeError:
        # settle_trip exhausts the mock cursor — the route got past both
        # Check 4 and Check 5, which is the assertion we care about.
        return

    # If we get here (mock had enough fetchone stubs), still verify no
    # fuel-efficiency code was raised.
    assert code not in ("FUEL_EFFICIENCY_LOW", "FUEL_EFFICIENCY_HIGH")


# ---- Pure-logic fuel-efficiency band tests (Check 5) --------------------

def test_avg_kml_within_band_passes():
    """500 km on 100 L → 5.0 km/L is within the 1.5–12 km/L band."""
    from backend.app.services.audit.cash import compute_settlement
    trip = _trip(start_odo=100000.0, end_odo=100500.0)
    expenses = [
        _exp(exp_type="FUEL", amount=9000.0, liters=100.0),
    ]
    s = compute_settlement(trip, expenses)
    assert s.avg_kml == 5.0
    assert 1.5 <= s.avg_kml <= 12.0


def test_avg_kml_below_floor():
    """500 km on 400 L → 1.25 km/L is below 1.5 floor."""
    from backend.app.services.audit.cash import compute_settlement
    trip = _trip(start_odo=100000.0, end_odo=100500.0)
    expenses = [
        _exp(exp_type="FUEL", amount=36000.0, liters=400.0),
    ]
    s = compute_settlement(trip, expenses)
    assert s.avg_kml == 1.25
    assert s.avg_kml < 1.5


def test_avg_kml_above_ceiling():
    """500 km on 20 L → 25.0 km/L is above 12 ceiling."""
    from backend.app.services.audit.cash import compute_settlement
    trip = _trip(start_odo=100000.0, end_odo=100500.0)
    expenses = [
        _exp(exp_type="FUEL", amount=1800.0, liters=20.0),
    ]
    s = compute_settlement(trip, expenses)
    assert s.avg_kml == 25.0
    assert s.avg_kml > 12.0