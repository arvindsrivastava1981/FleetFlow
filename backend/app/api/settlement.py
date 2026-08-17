"""Settlement router — list and manage settled trips.

Provides GET /settled-pdfs to list all trips with status SETTLED.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.core.config import settings
from backend.app.core.security import require_admin
from backend.app.db.connection import get_db
from backend.app.db.queries.settlement import get_settled_trips, get_trip_settlement_data

router = APIRouter()


@router.get("/settled-pdfs")
def list_settled_pdfs(request: Request) -> list[dict]:
    """List all trips with status SETTLED."""
    guard = require_admin(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        trips = get_settled_trips(conn)
        return trips