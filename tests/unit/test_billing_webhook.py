from __future__ import annotations

import json

from backend.app.db.queries.billing import (
    mark_webhook_processed,
    webhook_already_processed,
)


class _FakeCur:
    def __init__(self, row: list | None = None):
        self._row = row
        self.executed: list[tuple] = []

    def execute(self, sql: str, params=None) -> None:
        self.executed.append((sql, params))

    def fetchone(self):
        return self._row


class _FakeConn:
    def cursor(self, name=None):
        return _FakeCur()


def test_webhook_already_processed_returnstrue_when_event_logged():
    conn = _FakeConn()
    cur = _FakeCur(row=("id",))
    conn.cursor = lambda name=None: cur
    assert webhook_already_processed(conn, "evt_123") is True
    assert cur.executed[0][0].startswith("SELECT 1 FROM webhook_logs")
    assert cur.executed[0][1] == ("evt_123",)


def test_webhook_already_processed_returnstrue_when_not_logged():
    conn = _FakeConn()
    cur = _FakeCur(row=None)
    conn.cursor = lambda name=None: cur
    assert webhook_already_processed(conn, "evt_999") is False


def test_mark_webhook_processed_inserts_jsonb_payload():
    conn = _FakeConn()
    cur = _FakeCur()
    conn.cursor = lambda name=None: cur
    mark_webhook_processed(conn, "evt_123", "payment_link.paid", {"event": "x"})
    sql = cur.executed[0][0]
    params = cur.executed[0][1]
    assert sql.startswith("INSERT INTO webhook_logs")
    assert "%s::jsonb" in sql
    assert params[0] == "evt_123"
    assert params[1] == "payment_link.paid"
    assert json.loads(params[2]) == {"event": "x"}
