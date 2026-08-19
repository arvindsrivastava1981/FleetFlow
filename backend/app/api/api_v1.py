"""Phase 0 JSON API — transport-agnostic `/api/v1` router aggregator.

The former single-file router (auth, dashboard, trips, expenses, vehicles,
fleets, users, drivers, benchmarks, billing, rules, settlements) has been
decomposed into the `backend.app.api.v1` subpackage — one router per domain.
This module re-exports the aggregated `backend.app.api.v1.routers.router` so:

- `main.py` keeps mounting a single `api_v1.router` (paths/behavior unchanged),
- `backend.app.api.api_v1.*` imports referenced by tests keep resolving.

Guardrails carried over from the monolith:
  1. Real HTTP status codes (401/403) with JSON error payloads — never the
     browser 303 redirect, which fetch()/axios cannot consume cleanly.
  2. Auth via a Bearer token OR the session cookie (resolved through the same
     in-memory session store in core.security).
  3. No single-use CSRF token consumption on these JSON mutations — Bearer-in-
     header + a non-GET, non-form JSON content-type requirement suffix.
"""
from __future__ import annotations

from backend.app.api.v1.routers import router  # noqa: F401  (re-export)

__all__ = ["router"]