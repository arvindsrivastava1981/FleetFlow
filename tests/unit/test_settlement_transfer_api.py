"""SETTLEMENT_TRANSFER end-to-end API behavior (driver acceptance flow).

Covers: driver-only initiation with a server-computed amount, duplicate and
ledger-lock 409s, manager approval stamping driver consent, and the
LEDGER_CHANGED guard when the ledger drifted after initiation.
"""
from __future__ import annotations

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

DRIVER_USER = {"user_id": 2, "username": "driver", "role": "driver"}
MANAGER_USER = {"user_id": 1, "username": "manager", "role": "super_admin"}


def _db(fetchone_values, fetchall_value=None):
    cur = mock.MagicMock()
    cur.fetchone.side_effect = list(fetchone_values)
    cur.fetchall.return_value = fetchall_value or []
    cur.rowcount = 1  # driver_consent()/UPDATE paths compare rowcount > 0
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    db_obj = mock.MagicMock()
    db_obj.__enter__ = mock.MagicMock(return_value=conn)
    db_obj.__exit__ = mock.MagicMock(return_value=False)
    return db_obj


def _trip(**kw):
    base = {
        "id": 1,
        "trip_code": "TRIP-101",
        "vehicle_no": "MH12AB1234",
        "driver_user_id": 2,
        "status": "ACTIVE",
        "start_odo": 100000.0,
        "current_odo": 100500.0,
        "end_odo": None,
        "state_code": None,
        "created_by": 1,
        "fleet_id": 1,
    }
    base.update(kw)
    return base


def _exp(exp_type="FUEL", amount=100.0, approved_amount=None,
         manager_status="APPROVED", liters=10.0, created_by=None, id=99):
    return {
        "id": id,
        "trip_code": "TRIP-101",
        "exp_type": exp_type,
        "amount": amount,
        "approved_amount": approved_amount,
        "liters": liters,
        "manager_status": manager_status,
        "is_flagged": False,
        "odometer": 1000.0,
        "rate": 90.50,
        "created_by": created_by,
    }


def _ledger():
    """advance 20000 + goods 0 − (fuel 12500 + batta 2500) → net +5000."""
    return [
        _exp(exp_type="CASH_ADVANCE", amount=20000.0, liters=0.0),
        _exp(exp_type="DRIVER_SALARY", amount=2500.0, liters=0.0),
        _exp(exp_type="FUEL", amount=12500.0, liters=125.0),
    ]


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def resolve_db(monkeypatch):
    def _patch(db_obj, user=MANAGER_USER):
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
        monkeypatch.setattr(
            "backend.app.core.security.get_current_user", lambda request: user
        )
        monkeypatch.setattr(
            "backend.app.api.v1.deps.get_current_user", lambda request: user
        )

    return _patch


def test_driver_initiation_uses_server_computed_amount(client, resolve_db):
    """201 PENDING; the client-supplied amount is ignored for |net_balance|."""
    # fetchone order: trip lookup -> _trip_forbidden fleet row -> trip_status
    # -> open_settlement_request -> insert_expense trip_id reselect.
    db_obj = _db(
        [_trip(), {"fleet_id": 1}, {"status": "ACTIVE"}, None, {"id": 1}],
        fetchall_value=_ledger(),
    )
    resolve_db(db_obj, user=DRIVER_USER)

    resp = client.post(
        "/api/v1/expenses",
        json={"trip_code": "TRIP-101", "exp_type": "SETTLEMENT_TRANSFER",
              "amount": 1.0},
    )

    # NOTE: the API's `_created` helper responds 200 OK (project convention).
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["manager_status"] == "PENDING"
    assert body["settlement_amount"] == pytest.approx(5000.0)


def test_non_assigned_driver_cannot_initiate(client, resolve_db):
    db_obj = _db(
        [_trip(driver_user_id=77), {"fleet_id": 1}, {"status": "ACTIVE"}, None]
    )
    resolve_db(db_obj, user=DRIVER_USER)

    resp = client.post(
        "/api/v1/expenses",
        json={"trip_code": "TRIP-101", "exp_type": "SETTLEMENT_TRANSFER"},
    )

    assert resp.status_code == 403


def test_manager_cannot_initiate_on_behalf_of_driver(client, resolve_db):
    db_obj = _db([_trip(), {"status": "ACTIVE"}, None])
    resolve_db(db_obj, user=MANAGER_USER)

    resp = client.post(
        "/api/v1/expenses",
        json={"trip_code": "TRIP-101", "exp_type": "SETTLEMENT_TRANSFER"},
    )

    assert resp.status_code == 403


def test_duplicate_live_request_rejected(client, resolve_db):
    live = {"id": 9, "amount": 5000.0, "created_by": 2,
            "manager_status": "PENDING"}
    db_obj = _db([_trip(), {"fleet_id": 1}, {"status": "ACTIVE"}, live])
    resolve_db(db_obj, user=DRIVER_USER)

    resp = client.post(
        "/api/v1/expenses",
        json={"trip_code": "TRIP-101", "exp_type": "SETTLEMENT_TRANSFER"},
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "SETTLEMENT_ALREADY_INITIATED"


def test_ledger_locked_while_request_pending(client, resolve_db):
    """Road expenses are blocked until the manager resolves the request."""
    live = {"id": 9, "amount": 5000.0, "created_by": 2,
            "manager_status": "PENDING"}
    db_obj = _db([_trip(), {"fleet_id": 1}, {"status": "ACTIVE"}, live])
    resolve_db(db_obj, user=DRIVER_USER)

    resp = client.post(
        "/api/v1/expenses",
        json={"trip_code": "TRIP-101", "exp_type": "FUEL", "amount": 100},
    )

    assert resp.status_code == 409
    assert resp.json()["code"] == "SETTLEMENT_LOCKED"


def test_manager_approval_stamps_driver_consent(client, resolve_db):
    row = _exp(exp_type="SETTLEMENT_TRANSFER", amount=5000.0, liters=0.0,
               manager_status="PENDING", created_by=2, id=9)
    # fetchone order: expense->trip_code, trip lookup, expense row,
    # action_expense_status trip_code reselect.
    db_obj = _db(
        [{"trip_code": "TRIP-101"}, _trip(), row, {"trip_code": "TRIP-101"}],
        fetchall_value=_ledger(),
    )
    resolve_db(db_obj, user=MANAGER_USER)

    resp = client.post("/api/v1/expenses/9/action", json={"action": "APPROVE"})

    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "APPROVED"


def test_manager_approval_blocks_drifted_ledger(client, resolve_db):
    """If expenses changed after initiation, approve must fail LEDGER_CHANGED."""
    stale = _exp(exp_type="SETTLEMENT_TRANSFER", amount=9999.0, liters=0.0,
                 manager_status="PENDING", created_by=2, id=9)
    db_obj = _db([{"trip_code": "TRIP-101"}, _trip(), stale],
                 fetchall_value=_ledger())  # |net| is 5000, not 9999
    resolve_db(db_obj, user=MANAGER_USER)

    resp = client.post("/api/v1/expenses/9/action", json={"action": "APPROVE"})

    assert resp.status_code == 409
    assert resp.json()["code"] == "LEDGER_CHANGED"


# ---- Rejection wording + manager note ------------------------------------------


def test_reject_settlement_uses_settlement_labels_and_stores_reason(
    client, resolve_db
):
    """REJECT of a closing entry: settlement-specific bilingual wording and the
    manager's reason persisted into ``flag_reason``."""
    row = _exp(exp_type="SETTLEMENT_TRANSFER", amount=5000.0, liters=0.0,
               manager_status="PENDING", created_by=2, id=9)
    # fetchone order: expense->trip_code, trip lookup, expense row,
    # action_expense_status trip_code reselect.
    db_obj = _db(
        [{"trip_code": "TRIP-101"}, _trip(), row, {"trip_code": "TRIP-101"}]
    )
    resolve_db(db_obj, user=MANAGER_USER)

    resp = client.post(
        "/api/v1/expenses/9/action",
        json={"action": "REJECT", "reason": "Kanta receipt missing"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["label_en"] == "Settlement request rejected"
    assert body["label_hi"] == "हिसाब अस्वीकृत"
    cur = db_obj.__enter__.return_value.cursor.return_value
    upd = [
        c for c in cur.execute.call_args_list
        if str(c.args[0]).startswith("UPDATE expenses")
    ]
    assert upd, "status UPDATE never ran"
    assert upd[0].args[1] == ("REJECTED", "Kanta receipt missing", 9)


def test_reject_road_expense_keeps_plain_update_without_reason(
    client, resolve_db
):
    """No reason supplied -> status-only UPDATE; generic 'Deducted' wording."""
    row = _exp(exp_type="FUEL", amount=100.0)
    db_obj = _db(
        [{"trip_code": "TRIP-101"}, _trip(), row, {"trip_code": "TRIP-101"}]
    )
    resolve_db(db_obj, user=MANAGER_USER)

    resp = client.post("/api/v1/expenses/99/action", json={"action": "REJECT"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["label_en"] == "Deducted"
    cur = db_obj.__enter__.return_value.cursor.return_value
    upd = [
        c for c in cur.execute.call_args_list
        if str(c.args[0]).startswith("UPDATE expenses")
    ]
    assert upd[0].args[1] == ("REJECTED", 99)  # flag_reason untouched
