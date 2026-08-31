"""MISC receipt free-text: POST /expenses persists raw_receipt_text.

The WhatsApp view shows a Description box when the driver picks Kanta/Misc;
its value must land verbatim in `expenses.raw_receipt_text`.
"""
from __future__ import annotations

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

DRIVER_USER = {"user_id": 2, "username": "driver", "role": "driver"}


def _db(fetchone_values):
    cur = mock.MagicMock()
    cur.fetchone.side_effect = list(fetchone_values)
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    db_obj = mock.MagicMock()
    db_obj.__enter__ = mock.MagicMock(return_value=conn)
    db_obj.__exit__ = mock.MagicMock(return_value=False)
    return db_obj


def _trip():
    return {
        "id": 1, "trip_code": "TRIP-101", "vehicle_no": "MH12AB1234",
        "driver_user_id": 2, "status": "ACTIVE", "start_odo": 100000.0,
        "current_odo": 100500.0, "end_odo": None, "state_code": None,
        "created_by": 1, "fleet_id": 1,
    }


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def resolve_db(monkeypatch):
    def _patch(db_obj):
        monkeypatch.setattr("backend.app.api.v1.expenses.get_db", lambda: db_obj)
        monkeypatch.setattr(
            "backend.app.core.security.get_current_user",
            lambda request: DRIVER_USER,
        )
        monkeypatch.setattr(
            "backend.app.api.v1.deps.get_current_user",
            lambda request: DRIVER_USER,
        )

    return _patch


def _insert_calls(cur):
    return [
        c for c in cur.execute.call_args_list
        if "INSERT INTO expenses" in str(c.args[0])
    ]


def test_misc_expense_stores_raw_receipt_text(client, resolve_db):
    # fetchone order: trip lookup -> _trip_forbidden fleet row -> trip_status
    # -> open_settlement_request -> insert_expense trip_id reselect.
    db_obj = _db([_trip(), {"fleet_id": 1}, {"status": "ACTIVE"}, None, {"id": 1}])
    resolve_db(db_obj)

    resp = client.post(
        "/api/v1/expenses",
        json={
            "trip_code": "TRIP-101",
            "exp_type": "MISC",
            "amount": 1200,
            "raw_receipt_text": "Kanta at Bareilly weighbridge",
        },
    )

    assert resp.status_code == 200, resp.text
    cur = db_obj.__enter__.return_value.cursor.return_value
    ins = _insert_calls(cur)
    assert ins, "expense INSERT never ran"
    assert "raw_receipt_text" in str(ins[0].args[0])
    assert "Kanta at Bareilly weighbridge" in ins[0].args[1]


def test_misc_without_note_stores_null_raw_receipt_text(client, resolve_db):
    db_obj = _db([_trip(), {"fleet_id": 1}, {"status": "ACTIVE"}, None, {"id": 1}])
    resolve_db(db_obj)

    resp = client.post(
        "/api/v1/expenses",
        json={"trip_code": "TRIP-101", "exp_type": "MISC", "amount": 300},
    )

    assert resp.status_code == 200, resp.text
    cur = db_obj.__enter__.return_value.cursor.return_value
    ins = _insert_calls(cur)[0]
    assert "raw_receipt_text" in str(ins.args[0])
    assert ins.args[1][-1] is None  # blank note -> NULL column
