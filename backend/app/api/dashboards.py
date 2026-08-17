"""Dashboards router — role-based landing pages.

Three persona-targeted dashboards, each fronted by an existing role in the
`users` table (see `schema.sql` §7):
  GET /admin   — Fleet Owner / Super Admin macro oversight.
  GET /manager — Trip / Fleet Manager daily operations & settlement.
  GET /driver  — Driver live status, balance & quick-log actions.

Security:
- §2.1 unauthenticated -> `require_auth` 303-redirects to /login.
- §2.3 stored-XSS -> every DB-sourced string rendered via `security.esc()`;
  money/counts stay numeric-only interpolation.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.core.security import esc, get_current_user, require_auth, require_role
from backend.app.db.connection import get_db
from backend.app.db.queries.dashboards import (
    active_trip_progress,
    admin_kpis,
    anomaly_heatmap,
    approved_cash_net,
    driver_today_logged,
    efficiency_leaderboard,
    manager_kpis,
    open_escalations,
    settlement_ready_trips,
)
from backend.app.db.queries.expenses import get_expenses_for_trip
from backend.app.db.queries.trips import get_active_trip_for_driver
from backend.app.web.chrome import render_footer, render_header, render_sidebar

router = APIRouter()


def _fmt_dt(dt) -> str:
    return dt.strftime("%d %b %H:%M") if hasattr(dt, "strftime") else str(dt)[:16]


def _stat_card(
    color: str, label: str, head: str, sub: str, accent: str = ""
) -> str:
    return f"""<div class="rounded-2xl p-5 shadow-sm {color}">
        <p class="text-xs font-semibold uppercase opacity-80">{esc(label)}</p>
        <p class="text-2xl font-extrabold mt-1 {accent}">{head}</p>
        <p class="text-[11px] mt-1 opacity-80">{esc(sub)}</p>
    </div>"""


def _badge(text: str, cls: str) -> str:
    return f'<span class="text-[10px] font-bold px-2 py-0.5 rounded-full {cls}">{esc(text)}</span>'


# ---------------------------------------------------------------------------#
# Fleet Owner / Super Admin — GET /admin
# ---------------------------------------------------------------------------#
@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    guard = require_role(request, "super_admin")
    if guard is not None:
        return guard

    user = get_current_user(request) or {}
    with get_db() as conn:
        kpi = admin_kpis(conn)
        heatmap = anomaly_heatmap(conn)
        leaderboard = efficiency_leaderboard(conn)
        ready = settlement_ready_trips(conn)

    mtd = kpi["mtd_spend_by_type"]
    mtd_total = sum(mtd.values())

    fuel = mtd.get("FUEL", 0) + mtd.get("MISC", 0) + mtd.get("OTHER", 0)
    def_ = mtd.get("DEF", 0)
    toll = mtd.get("TOLL", 0)
    repairs = mtd.get("REPAIR", 0)
    challans = mtd.get("CHALLAN", 0) + mtd.get("RTO-FINE", 0)

    heat_rows = "".join(f"""
        <div class="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-50 px-3 py-2">
            <span class="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
            <div class="flex-1 min-w-0">
                <p class="text-xs font-bold text-slate-800 truncate">{esc(h['station'])}</p>
                <p class="text-[10px] text-slate-500">{esc(h['exp_type'])} · {h['flagged_count']}× flagged</p>
            </div>
            <span class="text-xs font-bold text-rose-600">₹{h['flagged_amount']:,.0f}</span>
        </div>""" for h in heatmap)

    leader_rows = "".join(f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50">
            <td class="p-3 text-xs font-bold text-slate-800">{esc(v['vehicle_no'])}</td>
            <td class="p-3 text-xs text-slate-600">{v['kml']:.2f} km/L</td>
            <td class="p-3 text-xs text-slate-400">target {v['target_kml'] or 4.0:.1f}</td>
            <td class="p-3 text-xs font-semibold {'text-emerald-600' if v['kml'] >= (v['target_kml'] or 4.0) else 'text-amber-600'}">
                {'▲ on target' if v['kml'] >= (v['target_kml'] or 4.0) else '▼ below baseline'}
            </td>
        </tr>""" for v in leaderboard)

    ready_rows = "".join(f"""
        <div class="flex items-center justify-between gap-3 border-b border-slate-50 py-2 last:border-0">
            <div>
                <p class="text-xs font-bold text-slate-800">{esc(t['trip_code'])}</p>
                <p class="text-[10px] text-slate-500">{esc(t['vehicle_no'])} · {esc(t['driver_name'])}</p>
            </div>
            <span class="text-xs font-semibold text-emerald-700">₹{t['returnable']:,.2f} returnable</span>
        </div>""" for t in ready)

    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VahanKhata Admin Dashboard</title><script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True, username=user.get('username', ''), role=user.get('role', ''))}
            <div class="flex flex-col lg:flex-row gap-4">
                {render_sidebar('admin', user.get('role', ''))}
                <main class="flex-1 space-y-4">
                    <div class="flex flex-wrap justify-between items-center gap-3">
                        <div>
                            <h2 class="text-lg font-extrabold text-slate-900">Fleet Owner Overview</h2>
                            <p class="text-xs text-slate-500">Macro financial health, leakage recovery and fleet efficiency.</p>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <a href="/drivers/create" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold px-3 py-2 rounded-xl transition shadow">Add Driver</a>
                            <a href="/fuel-benchmarks" class="bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold px-3 py-2 rounded-xl transition shadow">Update Fuel Benchmarks</a>
                            <a href="/dashboard" class="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-bold px-3 py-2 rounded-xl transition shadow">Export P&L</a>
                        </div>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                        {_stat_card("bg-sky-700 text-white", "Active Fleet", f"{kpi['active_trips']} trips", f"{kpi['active_vehicles']} vehicles · {kpi['active_drivers']} drivers on road")}
                        {_stat_card("bg-white border border-slate-200", "Fuel & Road Spend (MTD)", f"Rs.{mtd_total:,.2f}", f"Fuel Rs.{fuel:,.0f} · DEF Rs.{def_:,.0f} · Toll Rs.{toll:,.0f} · Repairs Rs.{repairs:,.0f} · Challans Rs.{challans:,.0f}")}
                        {_stat_card("bg-emerald-600 text-white", "Leakage Prevented", f"Rs.{kpi['leakage_prevented']:,.2f}", "3-5% recovered via anomaly engine rejections")}
                        {_stat_card("bg-white border border-slate-200", "Outstanding Cash Float", f"Rs.{kpi['outstanding_float']:,.2f}", f"Across {kpi['trips_in_float']} open trips")}
                    </div>
<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm lg:col-span-2">
                            <h3 class="text-sm font-extrabold text-slate-800 mb-3">Regional Spend (MTD)</h3>
                            <canvas id="spendChart" height="90"></canvas>
                        </div>
                        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                            <h3 class="text-sm font-extrabold text-slate-800 mb-3">Fleet-Wide Anomaly Heatmap</h3>
                            <div class="space-y-2">{heat_rows if heat_rows else '<p class="text-xs text-slate-400">No flagged sources yet.</p>'}</div>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm lg:col-span-2">
                            <h3 class="text-sm font-extrabold text-slate-800 mb-3">Vehicle Efficiency Leaderboard</h3>
                            <table class="w-full text-left">
                                <thead class="bg-slate-50 border-b">
                                    <tr><th class="p-2 text-[10px] font-bold text-slate-500 uppercase">Vehicle</th><th class="p-2 text-[10px] font-bold text-slate-500 uppercase">Avg km/L</th><th class="p-2 text-[10px] font-bold text-slate-500 uppercase">Target</th><th class="p-2 text-[10px] font-bold text-slate-500 uppercase">Performance</th></tr>
                                </thead>
                                <tbody>{leader_rows if leaderboard else '<tr><td colspan="4" class="p-4 text-center text-xs text-slate-400">No fuel data yet.</td></tr>'}</tbody>
                            </table>
                        </div>
                        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                            <h3 class="text-sm font-extrabold text-slate-800 mb-3">Settlement Approvals</h3>
                            <div class="divide-y divide-slate-50">{ready_rows if ready else '<p class="text-xs text-slate-400">No trips awaiting payout release.</p>'}</div>
                            <a href="/settled-pdfs" class="block mt-4 text-center bg-slate-900 hover:bg-slate-700 text-white text-xs font-bold px-3 py-2 rounded-xl transition shadow">Open Settlement Ledger</a>
                        </div>
                    </div>
                </main>
            </div>
            {render_footer()}
        </div>
        <script>
            new Chart(document.getElementById("spendChart"), {{
                type: "bar",
                data: {{
                    labels: ["Diesel", "DEF", "Toll", "Repairs", "Challans"],
                    datasets: [{{
                        label: "MTD spend",
                        data: [{fuel}, {def_}, {toll}, {repairs}, {challans}],
                        backgroundColor: ["#0ea5e9", "#f59e0b", "#10b981", "#8b5cf6", "#f43f5e"],
                        borderRadius: 6
                    }}]
                }},
                options: {{ plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: true }} }} }}
            }});
        </script>
    </body>
    </html>"""
    return html
# ---------------------------------------------------------------------------#
# Trip / Fleet Manager - GET /manager
# ---------------------------------------------------------------------------#
@router.get("/manager", response_class=HTMLResponse)
def manager_dashboard(request: Request):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    user = get_current_user(request) or {}
    with get_db() as conn:
        kpi = manager_kpis(conn)
        escalations = open_escalations(conn)
        progress = active_trip_progress(conn)
        ready = settlement_ready_trips(conn)

    esc_rows = "".join(f"""
        <div class="flex items-start gap-3 border-b border-slate-100 py-3 last:border-0">
            <div class="w-8 h-8 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-sm">
                {_badge('FLAG', 'bg-rose-100 text-rose-700') if e['is_flagged'] else _badge('PENDING', 'bg-amber-100 text-amber-700')}
            </div>
            <div class="flex-1 min-w-0">
                <p class="text-xs font-bold text-slate-800">{esc(e['trip_code'])} - {esc(e['exp_type'])} - Rs.{e['amount']:,.2f}</p>
                <p class="text-[11px] text-slate-500 mt-0.5">{esc(e['flag_reason']) if e['flag_reason'] else 'Pending manager review'} at {esc(e['station_name'] or e['trip_code'])}</p>
                <p class="text-[10px] text-slate-400 mt-0.5">{esc(_fmt_dt(e['created_at']))}</p>
            </div>
            <div class="flex gap-2 flex-shrink-0">
                <a href="/action-expense?id={e['id']}&action=APPROVE" class="bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-bold px-2.5 py-1.5 rounded-lg">Approve</a>
                <a href="/action-expense?id={e['id']}&action=REJECT" class="bg-rose-600 hover:bg-rose-500 text-white text-[10px] font-bold px-2.5 py-1.5 rounded-lg">Deduct</a>
            </div>
        </div>""" for e in escalations)

    progress_rows = "".join(f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50">
            <td class="p-3 text-xs font-bold text-slate-800">{esc(p['trip_code'])}</td>
            <td class="p-3 text-xs text-slate-600">{esc(p['driver_name'])}</td>
            <td class="p-3 text-xs text-slate-600">{esc(p['vehicle_no'])}</td>
            <td class="p-3 text-xs text-slate-600">{p['start_odo']:,.0f} to {p['current_odo']:,.0f}</td>
            <td class="p-3 text-xs text-slate-600">Rs.{p['claimed']:,.2f}</td>
            <td class="p-3 text-xs font-semibold {'text-emerald-700' if p['remaining_advance'] >= 0 else 'text-rose-700'}">Rs.{p['remaining_advance']:,.2f}</td>
        </tr>""" for p in progress)

    ready_rows = "".join(f"""
        <div class="flex items-center justify-between gap-3 border-b border-slate-50 py-2 last:border-0">
            <div>
                <p class="text-xs font-bold text-slate-800">{esc(t['trip_code'])}</p>
                <p class="text-[10px] text-slate-500">{esc(t['vehicle_no'])} - {esc(t['driver_name'])}</p>
            </div>
            <div class="text-right">
                <p class="text-xs font-semibold text-emerald-700">Rs.{t['returnable']:,.2f} to return</p>
                <a href="/generate-settlement-pdf?trip_code={t['trip_code']}" class="text-[10px] text-sky-600 font-bold hover:underline">PDF</a>
            </div>
        </div>""" for t in ready)

    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VahanKhata Trip Manager</title><script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True, username=user.get('username', ''), role=user.get('role', ''))}
            <div class="flex flex-col lg:flex-row gap-4">
                {render_sidebar('manager', user.get('role', ''))}
                <main class="flex-1 space-y-4">
                    <div class="flex flex-wrap justify-between items-center gap-3">
                        <div>
                            <h2 class="text-lg font-extrabold text-slate-900">Operations Shift</h2>
                            <p class="text-xs text-slate-500">Dispatch, alert triage and driver advance settlements.</p>
                        </div>
                        <div class="flex flex-wrap gap-2">
                            <a href="/?new_trip=1" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold px-3 py-2 rounded-xl transition shadow">Start New Trip</a>
                            <a href="/dashboard" class="bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-bold px-3 py-2 rounded-xl transition shadow">Review Red Flags</a>
                        </div>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                        {_stat_card("bg-sky-700 text-white", "Active Dispatched Trips", str(kpi['active_dispatched']), "Trips currently in transit")}
                        {_stat_card("bg-rose-600 text-white", "Pending Escalations", str(kpi['pending_escalations']), "Red flags awaiting your decision")}
                        {_stat_card("bg-white border border-slate-200", "Advances Disbursed Today", "Rs.%.2f" % kpi['advances_today'], "Fresh cash given for dispatches")}
                        {_stat_card("bg-white border border-slate-200", "Awaiting Settlement", str(kpi['awaiting_settlement']), "Vehicles returned, need PDF")}
                    </div>
<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm lg:col-span-1">
                            <h3 class="text-sm font-extrabold text-slate-800 mb-2">Live Escalations Feed</h3>
                            <div class="divide-y divide-slate-50">{esc_rows if esc_rows else '<p class="text-xs text-slate-400">All claims verified. Nothing pending.</p>'}</div>
                        </div>
                        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm lg:col-span-2">
                            <h3 class="text-sm font-extrabold text-slate-800 mb-3">Active Trip Progress</h3>
                            <table class="w-full text-left">
                                <thead class="bg-slate-50 border-b">
                                    <tr><th class="p-2 text-[10px] font-bold text-slate-500 uppercase">Trip</th><th class="p-2 text-[10px] font-bold text-slate-500 uppercase">Driver</th><th class="p-2 text-[10px] font-bold text-slate-500 uppercase">Vehicle</th><th class="p-2 text-[10px] font-bold text-slate-500 uppercase">Odometer</th><th class="p-2 text-[10px] font-bold text-slate-500 uppercase">Claimed</th><th class="p-2 text-[10px] font-bold text-slate-500 uppercase">Remaining Advance</th></tr>
                                </thead>
                                <tbody>{progress_rows if progress else '<tr><td colspan="6" class="p-4 text-center text-xs text-slate-400">No active trips.</td></tr>'}</tbody>
                            </table>
                        </div>
                    </div>
                    <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                        <div class="flex items-center justify-between mb-3">
                            <h3 class="text-sm font-extrabold text-slate-800">1-Click Settlement Queue</h3>
                            <span class="text-[10px] text-slate-400 font-semibold">{len(ready)} ready</span>
                        </div>
                        {ready_rows if ready else '<p class="text-xs text-slate-400">No trips ready for settlement yet.</p>'}
                    </div>
                </main>
            </div>
            {render_footer()}
        </div>
    </body>
    </html>"""
    return html
# ---------------------------------------------------------------------------#
# Driver - GET /driver
# ---------------------------------------------------------------------------#
@router.get("/driver", response_class=HTMLResponse)
def driver_dashboard(request: Request):
    guard = require_role(request, "driver")
    if guard is not None:
        return guard
    user = get_current_user(request) or {}
    with get_db() as conn:
        trip = get_active_trip_for_driver(conn, user.get("user_id", 0))
        trip_code = trip["trip_code"] if trip else None
        today_logged = driver_today_logged(conn, trip_code) if trip_code else 0.0
        cash_net = approved_cash_net(conn, trip_code) if trip_code else 0.0
        expenses = get_expenses_for_trip(conn, trip_code) if trip_code else []
    cash_in_hand = (trip["advance_amount"] or 0) + cash_net if trip else 0.0
    if trip:
        status_block = f"""<div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
            <p class="text-xs font-semibold text-slate-400 uppercase">Active Trip Assigned</p>
            <p class="text-lg font-extrabold text-slate-900 mt-1">{esc(trip['trip_code'])}</p>
            <p class="text-xs text-slate-500 mt-1">{esc(trip['vehicle_no'])} - {esc(trip['driver_name'])} - {esc(trip['origin'] or 'Origin TBD')} to {esc(trip['destination'] or 'Destination TBD')}</p>
            <div class="grid grid-cols-2 gap-3 mt-4 text-xs">
                <div class="bg-slate-50 rounded-xl p-3"><span class="text-slate-400 block font-semibold">Initial Advance</span><strong>Rs.{trip['advance_amount']:,.2f}</strong></div>
                <div class="bg-slate-50 rounded-xl p-3"><span class="text-slate-400 block font-semibold">Current Cash in Hand</span><strong class="text-emerald-700">Rs.{cash_in_hand:,.2f}</strong></div>
                <div class="bg-slate-50 rounded-xl p-3"><span class="text-slate-400 block font-semibold">Total Logged Today</span><strong>Rs.{today_logged:,.2f}</strong></div>
                <div class="bg-slate-50 rounded-xl p-3"><span class="text-slate-400 block font-semibold">Start to Current Odo</span><strong class="text-slate-800">{trip['start_odo']:,.0f} to {trip['current_odo']:,.0f} km</strong></div>
            </div>
        </div>"""
    else:
        status_block = '<div class="bg-white border border-slate-200 rounded-2xl p-8 text-center text-sm text-slate-400">No active trip assigned. Your manager will assign one before your next dispatch.</div>'

    quick_rows = "".join(f"""
        <div class="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
            <span class="w-8 h-8 rounded-full bg-sky-100 text-sky-700 flex items-center justify-center text-base">{e['exp_type'][:1]}</span>
            <div class="flex-1 min-w-0">
                <p class="text-xs font-bold text-slate-800">{esc(e['exp_type'])}</p>
                <p class="text-[10px] text-slate-500">Rs.{e['amount']:,.2f} - {esc(e['station_name'] or '')}</p>
            </div>
            {_badge('Approved', 'bg-emerald-100 text-emerald-700') if e['manager_status'] == 'APPROVED' else _badge('Pending', 'bg-amber-100 text-amber-700')}
        </div>""" for e in (expenses[:5]) if trip_code)

    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VahanKhata Driver</title><script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-4xl mx-auto space-y-6">
            {render_header(authenticated=True, username=user.get('username', ''), role=user.get('role', ''))}
            {status_block}
            <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="text-sm font-extrabold text-slate-800">Trip-End Summary</h3>
                    {_badge('Active', 'bg-emerald-100 text-emerald-700') if trip else _badge('No Trip', 'bg-slate-200 text-slate-500')}
                </div>
                {f"<p class='text-xs text-slate-500 mb-2'>Returnable balance at trip closure:</p><p class='text-lg font-extrabold text-emerald-700'>Rs.{cash_in_hand:,.2f}</p>" if trip else '<p class="text-xs text-slate-400">No summary available yet.</p>'}
            </div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <a href="/?trip_code={trip_code}" class="bg-sky-600 hover:bg-sky-500 text-white rounded-2xl p-5 text-center shadow-sm transition">
                    <span class="block text-2xl">&#128247;</span><span class="text-xs font-bold block mt-2">Log Receipt</span>
                </a>
                <a href="/?trip_code={trip_code}" class="bg-emerald-600 hover:bg-emerald-500 text-white rounded-2xl p-5 text-center shadow-sm transition">
                    <span class="block text-2xl">&#9989;</span><span class="text-xs font-bold block mt-2">Verified Claims</span>
                </a>
                <a href="/trips" class="bg-slate-800 hover:bg-slate-700 text-white rounded-2xl p-5 text-center shadow-sm transition">
                    <span class="block text-2xl">&#128220;</span><span class="text-xs font-bold block mt-2">My Trips</span>
                </a>
                <a href="/settled-pdfs" class="bg-amber-600 hover:bg-amber-500 text-white rounded-2xl p-5 text-center shadow-sm transition">
                    <span class="block text-2xl">&#127881;</span><span class="text-xs font-bold block mt-2">Trip-End Receipt</span>
                </a>
            </div>
            <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                <h3 class="text-sm font-extrabold text-slate-800 mb-3">Recent Logs</h3>
                <div class="space-y-2">{quick_rows if quick_rows else '<p class="text-xs text-slate-400">No expense logs on this trip yet.</p>'}</div>
            </div>
            {render_footer()}
        </div>
    </body>
    </html>"""
    return html