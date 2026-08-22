"""Notification-feed queries (feature F-3) — all derived from existing tables."""
from __future__ import annotations

from typing import Any


def pending_approvals(conn, manager_id: int | None = None) -> list[dict[str, Any]]:
    """PENDING expenses older than 24h.

    ``manager_id=None`` → fleet-wide (super admin view); otherwise only trips
    that manager created.
    """
    cur = conn.cursor()
    if manager_id is None:
        cur.execute(
            """SELECT e.id, e.exp_type, e.amount, e.created_at,
                      t.trip_code, t.vehicle_no
                 FROM expenses e
                 JOIN trips t ON t.trip_code = e.trip_code
                WHERE e.manager_status = 'PENDING'
                  AND e.created_at < NOW() - INTERVAL '24 hours'
                ORDER BY e.created_at
                LIMIT 20"""
        )
    else:
        cur.execute(
            """SELECT e.id, e.exp_type, e.amount, e.created_at,
                      t.trip_code, t.vehicle_no
                 FROM expenses e
                 JOIN trips t ON t.trip_code = e.trip_code
                WHERE e.manager_status = 'PENDING'
                  AND e.created_at < NOW() - INTERVAL '24 hours'
                  AND t.created_by = %s
                ORDER BY e.created_at
                LIMIT 20""",
            (manager_id,),
        )
    return cur.fetchall()


def fleet_trial_ending(conn, user_id: int | None) -> dict[str, Any] | None:
    """The caller's fleet row when its TRIAL ends within 3 days."""
    cur = conn.cursor()
    cur.execute(
        """SELECT f.id, f.owner_name, f.trial_ends_at
             FROM fleets f
             JOIN users u ON u.fleet_id = f.id
            WHERE u.id = %s
              AND f.subscription_status = 'TRIAL'
              AND f.trial_ends_at IS NOT NULL
              AND f.trial_ends_at <= NOW() + INTERVAL '3 days'""",
        (user_id,),
    )
    return cur.fetchone()


def settlement_ready_count(conn, manager_id: int | None = None) -> int:
    """ACTIVE trips with zero PENDING expenses (safe for 1-click settle)."""
    cur = conn.cursor()
    if manager_id is None:
        cur.execute(
            """SELECT COUNT(*) AS c FROM trips t
                WHERE t.status = 'ACTIVE'
                  AND NOT EXISTS (
                      SELECT 1 FROM expenses e
                       WHERE e.trip_code = t.trip_code
                         AND e.manager_status = 'PENDING')"""
        )
    else:
        cur.execute(
            """SELECT COUNT(*) AS c FROM trips t
                WHERE t.status = 'ACTIVE' AND t.created_by = %s
                  AND NOT EXISTS (
                      SELECT 1 FROM expenses e
                       WHERE e.trip_code = t.trip_code
                         AND e.manager_status = 'PENDING')""",
            (manager_id,),
        )
    return int(cur.fetchone()["c"])


def managers_with_emails(conn) -> list[dict[str, Any]]:
    """Active managers/super-admins with an email on file (digest recipients)."""
    cur = conn.cursor()
    cur.execute(
        """SELECT id, username, email, role
             FROM users
            WHERE role IN ('trip_manager', 'super_admin')
              AND is_active = TRUE AND email IS NOT NULL
            ORDER BY id"""
    )
    return cur.fetchall()
