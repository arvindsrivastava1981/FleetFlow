from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Iterator

import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection
from psycopg2.pool import SimpleConnectionPool

from backend.app.core.config import settings

# NUMERIC columns arrive as Decimal -> cast to float globally to avoid
# arithmetic TypeErrors exactly as the prototype's DEC2FLOAT did.
_DEC2FLOAT = psycopg2.extensions.new_type(
    psycopg2.extensions.DECIMAL.values,
    "DEC2FLOAT",
    lambda value, _cursor: float(value) if value is not None else None,
)
psycopg2.extensions.register_type(_DEC2FLOAT)
# Process-wide pool (audit R-2): reuses TCP+TLS connections instead of paying
# a fresh Neon handshake (~50-150 ms) on every request. Created lazily so
# forked/reloaded workers each build their own; SimpleConnectionPool is
# thread-safe for uvicorn's sync-endpoint threadpool. minconn=0 means nothing
# dials the database until the first real request needs a connection.
_pool: SimpleConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> SimpleConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = SimpleConnectionPool(
                    minconn=0,
                    maxconn=10,
                    dsn=settings.database_url,
                    cursor_factory=psycopg2.extras.RealDictCursor,
                    connect_timeout=10,
                )
    return _pool


def connect() -> PgConnection:
    """Open a standalone (unpooled) RealDictCursor connection."""
    return psycopg2.connect(
        settings.database_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
        # Bounded handshake so an unreachable/slow endpoint fails fast instead
        # of hanging request handling (TCP default can be ~21 s on Windows).
        connect_timeout=10,
    )


@contextmanager
def get_db() -> Iterator[PgConnection]:
    """Yield a **pooled** connection; commit unless error, then hand back.

    Commits on clean exit; rolls back + re-raises on exception. Connections
    that errored (or whose socket died) are discarded rather than recycled so
    one bad request cannot poison later ones.
    """
    conn = _get_pool().getconn()
    healthy = False
    try:
        yield conn
        conn.commit()
        healthy = True
    except Exception:
        try:
            conn.rollback()
            healthy = not conn.closed
        except Exception:  # noqa: BLE001 - rollback on a dead socket
            healthy = False
        raise
    finally:
        _get_pool().putconn(conn, close=not healthy)


def healthcheck() -> dict:
    """Return a lightweight DB liveness payload for /healthz."""
    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return {"db": "ok"}
    except Exception:  # noqa: BLE001 - health endpoint must never 500
        logging.getLogger(__name__).exception("healthcheck DB probe failed")
        return {"db": "error"}
