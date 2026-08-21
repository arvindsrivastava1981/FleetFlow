"""Tests for `GET /api/v1/fleets/subscriptions` (Super Admin consolidated view).

Covers:
  * Super Admin receives one consolidated row per fleet including
    `recent_events` — regression guard: every DB call must run on the OPEN
    connection from `get_db()`. The per-fleet events fetch previously ran
    AFTER the `with get_db()` block had closed the connection and crashed
    with `psycopg2.InterfaceError: connection already closed` (500).
  * An empty fleet table yields an empty list (no plan/event queries).
  * Non-super-admin roles are rejected with 403 FORBIDDEN.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest import mock

import psycopg2
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

MOCK_ADMIN = {"user_id": 1, "username": "admin", "role": "super_admin"}
MOCK_MANAGER = {"user_id": 2, "username": "mgr", "role": "trip_manager"}

_FLEET = {
    "id": 7,
    "owner_name": "Arvind Transport",
    "phone": "+91 99999 00000",
    "email": "billing@arvind.example",
    "plan_id": 2,
    "subscription_status": "TRIAL",
    "vehicle_count": 1,
    "vehicle_limit": 1,
    "trial_ends_at": None,
    "next_billing_date": None,
    "is_active": True,
    "entitlement_addons": {},
}
_PLAN = {"id": 2, "code": "MONTHLY", "name": "Monthly"}


class _FakeConn:
    """Minimal psycopg2 connection double that tracks `closed` like the real one."""

    def __init__(self):
        self.closed = False

    def cursor(self):
        if self.closed:
            raise psycopg2.InterfaceError("connection already closed")
        return mock.MagicMock()


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


@pytest.fixture
def subscriptions_db(monkeypatch):
    """Stub the billing module's DB surface with a connection that closes on exit.

    The stubbed `get_fleet_billing_events` mirrors the real query's behaviour of
    executing on the passed connection — it raises InterfaceError once the
    connection is closed, reproducing the pre-fix production failure mode.
    """
    import backend.app.api.v1.billing as billing

    conn = _FakeConn()

    @contextmanager
    def _fake_get_db():
        try:
            yield conn
        finally:
            conn.closed = True  # same guarantee as db.connection.get_db

    monkeypatch.setattr(billing, "get_db", _fake_get_db)
    monkeypatch.setattr(
        billing, "get_all_fleets",
        lambda c, fleet_id=None: list([] if getattr(c, "closed", True) else [_FLEET]),
    )
    monkeypatch.setattr(billing, "get_all_plans", lambda c: [_PLAN])

    calls = {}

    def _fake_events(c, fid, limit=50):
        if getattr(c, "closed", False):
            raise psycopg2.InterfaceError("connection already closed")
        calls["fid"] = fid
        calls["limit"] = limit
        return [{"id": 9, "event_type": "TRIAL_START", "plan_code": "TRIAL"}]

    monkeypatch.setattr(billing, "get_fleet_billing_events", _fake_events)
    return {"events_calls": calls}


def test_subscriptions_consolidated_rows(client, admin_session, subscriptions_db):
    """One consolidated row per fleet; events fetched on the open connection."""
    resp = client.get("/api/v1/fleets/subscriptions")
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]
    assert len(rows) == 1
    row = rows[0]
    assert row["fleet_id"] == 7
    assert row["owner_name"] == "Arvind Transport"
    assert row["phone"] == "+91 99999 00000"
    # plan_code/plan_name resolve through the subscription_plans join.
    assert row["plan_code"] == "MONTHLY"
    assert row["plan_name"] == "Monthly"
    assert row["subscription_status"] == "TRIAL"
    assert row["vehicle_count"] == 1
    assert row["is_active"] is True
    # Recent events were fetched per-fleet on the OPEN connection with limit=5.
    assert row["recent_events"][0]["event_type"] == "TRIAL_START"
    assert subscriptions_db["events_calls"] == {"fid": 7, "limit": 5}


def test_subscriptions_empty_table_returns_empty_list(client, admin_session, monkeypatch):
    """No fleets → 200 with [] (plans/events never queried)."""
    import backend.app.api.v1.billing as billing

    conn = _FakeConn()

    @contextmanager
    def _fake_get_db():
        yield conn

    monkeypatch.setattr(billing, "get_db", _fake_get_db)
    monkeypatch.setattr(billing, "get_all_fleets", lambda c, fleet_id=None: [])

    resp = client.get("/api/v1/fleets/subscriptions")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == []


def test_subscriptions_requires_super_admin(client, monkeypatch):
    """A trip_manager gets 403 FORBIDDEN (route is super_admin-only)."""
    import backend.app.core.security as sec
    from backend.app.api.v1 import deps

    monkeypatch.setattr(sec, "get_current_user", lambda request: MOCK_MANAGER)
    monkeypatch.setattr(deps, "get_current_user", lambda request: MOCK_MANAGER)

    resp = client.get("/api/v1/fleets/subscriptions")
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "FORBIDDEN"