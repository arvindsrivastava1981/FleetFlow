"""Daily maintenance job (feature F-8) — schedule via Render Cron / GH Actions.

Steps:
1. Purge expired ``auth_sessions`` rows (R-1 housekeeping).
2. Best-effort refresh of live fuel benchmarks (falls back to the static
   snapshot when the scraper/network is unavailable).
3. Print a short summary; exit code reflects hard failures only.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    ok = True

    print("[1/2] purge expired auth sessions")
    purged = -1
    try:
        from backend.app.db.connection import get_db
        from backend.app.db.queries import auth_store

        with get_db() as conn:
            purged = auth_store.delete_expired_auth_sessions(conn)
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"      FAILED: {exc}")
    print(f"      rows deleted: {purged}")

    print("[2/2] refresh live fuel benchmarks")
    touched = -1
    try:
        from backend.app.db.connection import get_db
        from backend.app.db.queries.benchmarks import upsert_benchmarks_from_live
        from backend.app.services.fuel_live import get_live_prices

        rows = get_live_prices()
        if not rows:
            print("      no live prices returned — keeping snapshot")
        else:
            with get_db() as conn:
                touched = upsert_benchmarks_from_live(conn, rows)
            print(f"      states updated: {touched}")
    except Exception as exc:  # noqa: BLE001 - snapshot fallback is fine
        print(f"      SKIPPED: {exc}")

    print("CRON", "OK" if ok else "PARTIAL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
