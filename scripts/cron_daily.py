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

from backend.app.core.config import settings  # noqa: E402


def main() -> int:
    ok = True

    print("[1/3] purge expired auth sessions")
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

    print("[2/3] refresh live fuel benchmarks")
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

    print("[3/3] manager email digests")
    try:
        from backend.app.db.connection import get_db
        from backend.app.db.queries.notifications import (
            fleet_trial_ending,
            managers_with_emails,
            pending_approvals,
            settlement_ready_count,
        )
        from backend.app.services.email.client import dispatch_sync, send_email

        with get_db() as conn:
            recipients = managers_with_emails(conn)
        dispatched = 0
        for m in recipients:
            scope = m["id"] if m["role"] == "trip_manager" else None
            with get_db() as conn:
                pending = pending_approvals(conn, scope)
                ready = settlement_ready_count(conn, scope)
                trial = fleet_trial_ending(conn, m["id"])
            if not pending and not ready and not trial:
                continue
            lines = [f"Hello {m['username']},", "", "Your VahanKhata daily digest:"]
            if pending:
                lines.append(f"• {len(pending)} expense(s) awaiting approval >24h")
            if ready:
                lines.append(f"• {ready} trip(s) ready to settle")
            if trial:
                lines.append(
                    f"• Trial for fleet '{trial['owner_name']}' ends "
                    f"{trial['trial_ends_at'].isoformat()[:10]}"
                )
            lines += ["", f"— {settings.support_email}"]
            body_text = "\n".join(lines)
            dispatch_sync(
                send_email,
                to_email=m["email"],
                subject="VahanKhata daily digest",
                body=body_text,
                html_body=f"<pre style=\"font-family:inherit\">{body_text}</pre>",
            )
            dispatched += 1
        print(f"      digests dispatched: {dispatched}")
    except Exception as exc:  # noqa: BLE001 - email is best-effort
        print(f"      SKIPPED: {exc}")

    print("CRON", "OK" if ok else "PARTIAL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
