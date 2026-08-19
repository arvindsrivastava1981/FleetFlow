"""Versioned `/api/v1` routers (subpackage of `backend/app/api`).

This package decomposes the former single-file `api/api_v1.py` monolith into
per-domain routers so each resource (trips, expenses, vehicles, fleets, users,
auth, billing, benchmarks, dashboard, rules) owns its HTTP wiring. All routers
share:

- `deps.py`: the `/api/v1` prefix + serialization/response helpers
  (``_ok``, ``_created``, ``_bad``, ``_not_found``, ``_identity``,
  ``_trip_forbidden``, ``_read_json_body``).
- `schemas` (``backend.app.schemas.api_v1``): typed Pydantic response models.

`api_v1.py` (the parent module) imports every sub-router and mounts them under
the single `/api/v1/*` prefix, so route paths and behavior are unchanged. The
note in `api/__init__.py` (only two routers mounted) still holds — `main.py`
mounts `api_v1.router` (which aggregates these) plus the webhook router.
"""
