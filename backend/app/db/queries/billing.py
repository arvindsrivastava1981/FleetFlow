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
