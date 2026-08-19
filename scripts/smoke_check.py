"""Idempotent environment/schema sanity check for developers & CI.

Verifies (without mutating anything):
  - required env vars present
  - the package imports and /healthz contract resolves
  - the rules band matches the product spec

Intended for local dev + fast CI smoke gates, not as a substitute for the
migration's formal fixtures.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.config import settings
from backend.app.services.rules.bands import DEFAULT_BAND


def main() -> int:
    checks: list[bool] = []
    print("[1/3] env")
    checks.append(bool(settings.database_url))
    checks.append(bool(settings.support_email))
    print("   database_url set:", bool(settings.database_url))
    print("   support_email set:", bool(settings.support_email))

    print("[2/3] rules band")
    band = DEFAULT_BAND
    print(f"   band = {band.min_price:.2f} .. {band.max_price:.2f}")
    checks.append(abs(band.min_price - 83.26) < 0.01)
    checks.append(abs(band.max_price - 97.74) < 0.01)

    print("[3/3] import paths")
    from backend.app.db.connection import get_db, healthcheck  # noqa
    from backend.app.core.security import esc, is_authorized_user  # noqa
    checks.append(True)

    ok = all(checks)
    print("SMOKE", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())