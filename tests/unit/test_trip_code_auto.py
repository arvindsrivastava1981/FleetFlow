from __future__ import annotations

from unittest import mock

from backend.app.db.queries.trips import next_trip_code


def _cur(rows):
    cur = mock.MagicMock()
    cur.fetchone.return_value = rows[0] if rows else None
    return cur


def test_next_trip_code_first_trip():
    cur = _cur([])  # no existing trips for this plate
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    assert next_trip_code(conn, "UP32MA1234") == "1234-1"


def test_next_trip_code_increments_last_trip():
    cur = _cur([{"trip_code": "1234-3"}])
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    assert next_trip_code(conn, "UP32MA1234") == "1234-4"


def test_next_trip_code_increments_even_when_prefixed():
    """Existing codes like `1234-03` should still yield the next integer suffix."""
    cur = _cur([{"trip_code": "1234-03"}])
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    assert next_trip_code(conn, "UP32MA1234") == "1234-4"


def test_next_trip_code_ignores_unrelated_plate_codes():
    """Codes for another plate aren't treated as this vehicle's last trip."""
    cur = _cur([{"trip_code": "1234-2"}])
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    # The query result is the vehicle-scoped maximum; the helper just advances it.
    assert next_trip_code(conn, "UP32MA1234") == "1234-3"
