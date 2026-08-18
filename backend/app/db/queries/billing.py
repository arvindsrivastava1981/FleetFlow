"""Query helpers for the `webhook_logs` table (Razorpay webhook idempotency).

The webhook route writes a `webhook_logs` row *inside the same transaction* that
applies the event's side effect, keyed by the stable Razorpay `event.id`. A
retried delivery of the same event hits the UNIQUE(event_id) constraint and is a
no-op, so activation / vehicle-limit bumps can never be applied twice.

All functions take a live `psycopg2` connection (from `db/connection.get_db()`)
and do NOT commit — the caller's `get_db()` contextmanager commits on clean exit.
"""
from __future__ import annotations

import json


def webhook_already_processed(conn, event_id: str) -> bool:
    """True when a webhook event has already been handled (idempotency guard)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM webhook_logs WHERE event_id = %s",
        (event_id,),
    )
    return cur.fetchone() is not None


def mark_webhook_processed(
    conn,
    event_id: str,
    event_type: str,
    payload: dict,
    status: str = "PROCESSED",
) -> None:
    """Record a processed webhook event.

    Must be called inside the transaction that also applies the event's side
    effect so the log row commits atomically with it. Raises on a duplicate
    event_id (UNIQUE violation) — callers should treat that as a retry and no-op.
    """
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO webhook_logs (event_id, event_type, payload, status) "
        "VALUES (%s, %s, %s::jsonb, %s)",
        (event_id, event_type, json.dumps(payload, default=str), status),
    )