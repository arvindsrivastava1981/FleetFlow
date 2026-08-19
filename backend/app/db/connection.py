from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection

from backend.app.core.config import settings

# NUMERIC columns arrive as Decimal -> cast to float globally to avoid
# arithmetic TypeErrors exactly as the prototype's DEC2FLOAT did.
_DEC2FLOAT = psycopg2.extensions.new_type(
    psycopg2.extensions.DECIMAL.values,
    "DEC2FLOAT",
    lambda value, _cursor: float(value) if value is not None else None,
)
psycopg2.extensions.register_type(_DEC2FLOAT)


def connect() -> PgConnection:
    """Open a new RealDictCursor connection to the configured database."""
    return psycopg2.connect(
        settings.database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


@contextmanager
def get_db() -> Iterator[PgConnection]:
    """Yield a connection and guarantee it is closed (commit unless error).

    Usage:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(...)
            rows = cur.fetchall()
    Commits on clean exit; rolls back + re-raises on exception.
    """
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def healthcheck() -> dict:
    """Return a lightweight DB liveness payload for /healthz."""
    try:
        with connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return {"db": "ok"}
    except Exception as exc:  # noqa: BLE001 - health endpoint must never 500
        return {"db": "error", "detail": str(exc)}