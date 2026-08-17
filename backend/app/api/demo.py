"""Dev demo router — data reset.

Fixes from deep_agent_recommendation:
- §2.1 (CRITICAL): `/reset-demo` previously wiped all `expenses` + `trips` with
  NO authentication. Here it requires `require_auth`; anonymous access is
  redirected to `/login` (preventing a one-click data wipe via a crafted link).
Clears transactional rows only — no DDL, no reseed (matches prior behaviour).
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from backend.app.core.security import require_auth
from backend.app.db.connection import get_db

router = APIRouter()


@router.get("/reset-demo")
def reset_demo(request: Request):
    guard = require_auth(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses")
        cur.execute("DELETE FROM trips")
    return RedirectResponse(url="/", status_code=303)