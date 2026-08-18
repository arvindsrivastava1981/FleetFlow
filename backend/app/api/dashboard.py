"""Dashboard router — authenticated landing page shown after login.

Migrated from `fleetflow_interactive_demo.py`'s `/dashboard` savings view so
that the post-login redirect in `auth.py` (`url="/dashboard"`) resolves
instead of returning 404. Until this route was ported, only the action/API
routers (auth/trips/expenses/demo) were wired into the modular app, so the
landing page the login handler pointed at did not exist.

Security:
- §2.1 unauthenticated access -> `require_auth` 303-redirects to /login.
- §2.3 stored-XSS -> DB-sourced trip codes are embedded as JSON with `<`,
  `>`, `&` neutralized to \\uXXXX (safe inside a <script> block); every money
  figure is numeric-only (`₹<float>`) and never interpolates raw DB text.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from backend.app.core.security import get_current_user, require_auth
from backend.app.db.connection import get_db
from backend.app.web.chrome import render_footer, render_header, render_sidebar

router = APIRouter()


_DASHBOARD_TOTALS = """SELECT COALESCE(SUM(amount), 0) AS total_claimed,
                              COALESCE(SUM(CASE WHEN manager_status = 'REJECTED' THEN amount ELSE 0 END), 0) AS money_saved,
                              COALESCE(SUM(CASE WHEN manager_status = 'APPROVED' OR (NOT is_flagged AND manager_status != 'REJECTED') THEN amount ELSE 0 END), 0) AS total_approved,
                              COALESCE(SUM(CASE WHEN manager_status = 'PENDING' THEN 1 ELSE 0 END), 0) AS pending_count
                       FROM expenses"""

_SAVINGS_BY_TRIP = """SELECT trip_code,
                             COALESCE(SUM(CASE WHEN manager_status = 'REJECTED' THEN amount ELSE 0 END), 0) AS saved
                      FROM expenses GROUP BY trip_code
                      HAVING COALESCE(SUM(CASE WHEN manager_status = 'REJECTED' THEN amount ELSE 0 END), 0) > 0
                      ORDER BY saved DESC LIMIT 6"""


def _safe_json(obj) -> str:
    """json.dumps, neutralizing <, >, & so the result is safe inside a <script> block."""
    return (
        json.dumps(obj)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


@router.get("/dashboard", response_class=HTMLResponse)
def savings_dashboard(request: Request):
    guard = require_auth(request)
    if guard is not None:
        return guard

    user = get_current_user(request) or {}
    # Scope all figures to trips the logged-in user created (trip_manager) or
    # the trips assigned to them (driver); super_admin sees everything.
    if user.get("role") == "trip_manager":
        # Join against the manager's own trips for both totals and per-trip rows.
        totals_sql = """SELECT COALESCE(SUM(e.amount), 0) AS total_claimed,
                               COALESCE(SUM(CASE WHEN e.manager_status = 'REJECTED' THEN e.amount ELSE 0 END), 0) AS money_saved,
                               COALESCE(SUM(CASE WHEN e.manager_status = 'APPROVED' OR (NOT e.is_flagged AND e.manager_status != 'REJECTED') THEN e.amount ELSE 0 END), 0) AS total_approved,
                               COALESCE(SUM(CASE WHEN e.manager_status = 'PENDING' THEN 1 ELSE 0 END), 0) AS pending_count
                          FROM expenses e
                          JOIN trips t ON t.trip_code = e.trip_code
                         WHERE t.created_by = %s"""
        trips_count_sql = "SELECT COUNT(*) AS trip_count FROM trips WHERE created_by = %s"
        savings_sql = """SELECT e.trip_code,
                                COALESCE(SUM(CASE WHEN e.manager_status = 'REJECTED' THEN e.amount ELSE 0 END), 0) AS saved
                           FROM expenses e
                           JOIN trips t ON t.trip_code = e.trip_code
                          WHERE t.created_by = %s
                          GROUP BY e.trip_code
                         HAVING COALESCE(SUM(CASE WHEN e.manager_status = 'REJECTED' THEN e.amount ELSE 0 END), 0) > 0
                          ORDER BY saved DESC LIMIT 6"""
        scope_params = (user.get("user_id"),)
    elif user.get("role") == "driver":
        totals_sql = """SELECT COALESCE(SUM(e.amount), 0) AS total_claimed,
                               COALESCE(SUM(CASE WHEN e.manager_status = 'REJECTED' THEN e.amount ELSE 0 END), 0) AS money_saved,
                               COALESCE(SUM(CASE WHEN e.manager_status = 'APPROVED' OR (NOT e.is_flagged AND e.manager_status != 'REJECTED') THEN e.amount ELSE 0 END), 0) AS total_approved,
                               COALESCE(SUM(CASE WHEN e.manager_status = 'PENDING' THEN 1 ELSE 0 END), 0) AS pending_count
                          FROM expenses e
                          JOIN trips t ON t.trip_code = e.trip_code
                         WHERE t.driver_user_id = %s"""
        trips_count_sql = "SELECT COUNT(*) AS trip_count FROM trips WHERE driver_user_id = %s"
        savings_sql = """SELECT e.trip_code,
                                COALESCE(SUM(CASE WHEN e.manager_status = 'REJECTED' THEN e.amount ELSE 0 END), 0) AS saved
                           FROM expenses e
                           JOIN trips t ON t.trip_code = e.trip_code
                          WHERE t.driver_user_id = %s
                          GROUP BY e.trip_code
                         HAVING COALESCE(SUM(CASE WHEN e.manager_status = 'REJECTED' THEN e.amount ELSE 0 END), 0) > 0
                          ORDER BY saved DESC LIMIT 6"""
        scope_params = (user.get("user_id"),)
    else:
        totals_sql = _DASHBOARD_TOTALS
        trips_count_sql = "SELECT COUNT(*) AS trip_count FROM trips"
        savings_sql = _SAVINGS_BY_TRIP
        scope_params = ()

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(totals_sql, scope_params)
        totals = cur.fetchone()
        cur.execute(trips_count_sql, scope_params)
        trip_count = cur.fetchone()["trip_count"]
        cur.execute(savings_sql, scope_params)
        savings_by_trip = cur.fetchall()

    money_saved = totals["money_saved"] or 0
    total_claimed = totals["total_claimed"] or 0
    total_approved = totals["total_approved"] or 0
    pending_count = totals["pending_count"] or 0

    chart_labels = _safe_json(
        [row["trip_code"] for row in savings_by_trip] or ["No rejections yet"]
    )
    chart_values = _safe_json([row["saved"] for row in savings_by_trip] or [0])

    user = get_current_user(request) or {}
    return f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VahanKhata Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True, username=user.get('username', ''), role=user.get('role', ''))}
            <div class="flex flex-col lg:flex-row gap-4">
                {render_sidebar("dashboard", user.get('role', 'super_admin'))}
                <main class="flex-1 space-y-4">
                    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                        <div class="bg-emerald-600 text-white rounded-2xl p-5 shadow-sm">
                            <p class="text-xs font-semibold text-emerald-100 uppercase">Money Saved So Far</p>
                            <p class="text-2xl font-extrabold mt-1">₹{money_saved:,.2f}</p>
                            <p class="text-[11px] text-emerald-100 mt-1">Flagged claims rejected instead of paid out</p>
                        </div>
                        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                            <p class="text-xs font-semibold text-slate-400 uppercase">Total Claimed</p>
                            <p class="text-2xl font-extrabold mt-1 text-slate-900">₹{total_claimed:,.2f}</p>
                        </div>
                        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                            <p class="text-xs font-semibold text-slate-400 uppercase">Total Approved</p>
                            <p class="text-2xl font-extrabold mt-1 text-slate-900">₹{total_approved:,.2f}</p>
                        </div>
                        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                            <p class="text-xs font-semibold text-slate-400 uppercase">Pending Reviews</p>
                            <p class="text-2xl font-extrabold mt-1 text-amber-600">{pending_count}</p>
                            <p class="text-[11px] text-slate-400 mt-1">Across {trip_count} trips</p>
                        </div>
                    </div>
                    <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                        <h2 class="text-sm font-extrabold text-slate-800 mb-3">Money Saved by Trip</h2>
                        <canvas id="savingsChart" height="110"></canvas>
                    </div>
                </main>
            </div>
            {render_footer()}
        </div>
        <script>
            new Chart(document.getElementById("savingsChart"), {{
                type: "bar",
                data: {{
                    labels: {chart_labels},
                    datasets: [{{
                        label: "Money saved (₹)",
                        data: {chart_values},
                        backgroundColor: "#059669",
                        borderRadius: 6
                    }}]
                }},
                options: {{
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{ y: {{ beginAtZero: true }} }}
                }}
            }});
        </script>
    </body>
    </html>"""
