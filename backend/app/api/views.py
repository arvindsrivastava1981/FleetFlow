"""Views router — trips listing, overview, and the 3-column workspace.

Migrated from `fleetflow_interactive_demo.py`'s `GET /`, `GET /trips`, and
`GET /` routes (the read-only UI pages that were last on the prototype).

Security:
- §2.1 unauthenticated access -> `require_auth` 303-redirects to /login.
- §2.3 stored-XSS -> every DB-sourced string value rendered via
  `security.esc()`; money/counters stay numeric-only interpolation.
"""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.core.security import esc, get_current_user, require_auth
from backend.app.db.connection import get_db
from backend.app.db.queries.expenses import get_expenses_for_trip
from backend.app.db.queries.trips import (
    get_latest_active_trip_for_user,
    get_trip_by_code,
    get_trip_stats_by_code,
    get_trips_for_user,
)
from backend.app.db.queries.users import get_users_by_roles
from backend.app.db.queries.vehicles import get_all_vehicles
from backend.app.web.chrome import render_footer, render_header, render_sidebar

router = APIRouter()

GOODS_EXPENSE_TYPES = ("GOODS_BUY", "GOODS_SALE")


def _fmt_dt(dt) -> str:
    return dt.strftime("%d %b %H:%M") if hasattr(dt, "strftime") else str(dt)[:16]


def _owns_trip(trip: dict, user: dict) -> bool:
    """Whether *user* is allowed to view *trip*.

    super_admin sees everything; trip_manager only their own; driver only assigned.
    """
    role = user.get("role")
    if role == "super_admin":
        return True
    if role == "trip_manager":
        return trip.get("created_by") == user.get("user_id")
    if role == "driver":
        return trip.get("driver_user_id") == user.get("user_id")
    return False


def _is_approved(expense: dict) -> bool:
    return expense["manager_status"] == "APPROVED"


def _approved_cash_impact(expense: dict) -> float:
    if not _is_approved(expense):
        return 0.0
    return expense["amount"] if expense["exp_type"] == "GOODS_SALE" else -expense["amount"]


@router.get("/trips", response_class=HTMLResponse)
def trip_listing(request: Request):
    guard = require_auth(request)
    if guard is not None:
        return guard

    user = get_current_user(request) or {}
    with get_db() as conn:
        all_trips = get_trips_for_user(conn, user.get("user_id"), user.get("role", "super_admin"))
        stats_by_trip = get_trip_stats_by_code(conn)

    all_trips_settled = not all_trips or all(t["status"] in ("SETTLED", "CANCELLED") for t in all_trips)
    trip_rows = "".join([f"""
        <a href="/?trip_code={t['trip_code']}" class="block bg-white border {'border-sky-300 ring-2 ring-sky-100' if t['status'] == 'ACTIVE' else 'border-slate-200'} rounded-2xl p-5 shadow-sm hover:shadow-md transition">
            <div class="flex flex-wrap justify-between gap-3 items-start">
                <div>
                    <div class="flex items-center gap-2">
                        <h2 class="font-extrabold text-slate-900">{esc(t['trip_code'])}</h2>
                        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full {'bg-emerald-100 text-emerald-800' if t['status'] == 'ACTIVE' else 'bg-slate-200 text-slate-700'}">{esc(t['status'])}</span>
                    </div>
                    <p class="text-xs text-slate-500 mt-1">{esc(t['vehicle_no'])} · {esc(t['driver_name'])}</p>
                </div>
                <span class="text-xs text-sky-700 font-bold">View trip details →</span>
            </div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5 text-xs">
                <div><span class="text-slate-400 block">Advance</span><strong>₹{t['advance_amount']:,.2f}</strong></div>
                <div><span class="text-slate-400 block">Claims</span><strong>₹{stats_by_trip.get(t['trip_code'], {}).get('total_claimed', 0):,.2f}</strong></div>
                <div><span class="text-slate-400 block">Approved</span><strong class="text-emerald-700">₹{stats_by_trip.get(t['trip_code'], {}).get('total_approved', 0):,.2f}</strong></div>
                <div><span class="text-slate-400 block">Pending reviews</span><strong class="text-amber-700">{stats_by_trip.get(t['trip_code'], {}).get('pending_count', 0)}</strong></div>
            </div>
        </a>""" for t in all_trips])

    start_trip_control = (
        '<a href="/?new_trip=1" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition shadow">➕ Start New Trip</a>'
        if all_trips_settled
        else '<span class="bg-slate-200 text-slate-400 text-xs font-bold px-4 py-2.5 rounded-xl cursor-not-allowed" title="Settle the current trip before starting another">➕ Start New Trip</span>'
    )
    return f"""<!DOCTYPE html>
    <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>VahanKhata Trips</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-5xl mx-auto space-y-6">
            {render_header(authenticated=True, username=user.get('username', ''), role=user.get('role', ''))}
            {render_sidebar("trips", user.get('role', 'super_admin'))}
            <div class="flex items-center justify-between"><div><h2 class="text-lg font-extrabold text-slate-900">All Trips</h2><p class="text-xs text-slate-500">Select a trip to open its complete ledger, audit thread, and settlement details.</p></div>{start_trip_control}<span class="text-xs text-slate-400">{len(all_trips)} total</span></div>
            <div class="space-y-3">{trip_rows if trip_rows else '<div class="bg-white border border-slate-200 rounded-2xl p-10 text-center text-sm text-slate-400">No trips yet. Start your first trip above.</div>'}</div>
            {render_footer()}
        </div>
    </body></html>"""


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    guard = require_auth(request)
    if guard is not None:
        return guard

    user = get_current_user(request) or {}
    with get_db() as conn:
        all_trips = get_trips_for_user(conn, user.get("user_id"), user.get("role", "super_admin"))
        stats_by_trip = get_trip_stats_by_code(conn)

    rows_html = "".join([f"""
    <tr class="border-b border-slate-100 hover:bg-slate-50">
        <td class="p-3 text-xs font-bold text-slate-800">{esc(t['trip_code'])}</td>
        <td class="p-3 text-xs text-slate-600">{esc(t['vehicle_no'])}</td>
        <td class="p-3 text-xs text-slate-600">{esc(t['driver_name'])}</td>
        <td class="p-3 text-xs">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold {'bg-emerald-100 text-emerald-700' if t['status'] == 'ACTIVE' else 'bg-slate-200 text-slate-600'}">{esc(t['status'])}</span>
        </td>
        <td class="p-3 text-xs text-slate-600">₹{t['advance_amount']:,.2f}</td>
        <td class="p-3 text-xs text-slate-600">{stats_by_trip.get(t['trip_code'], {}).get('expense_count', 0)}</td>
        <td class="p-3 text-xs text-rose-600 font-semibold">₹{stats_by_trip.get(t['trip_code'], {}).get('flagged_amount', 0):,.2f}</td>
        <td class="p-3 text-xs text-amber-600 font-semibold">{stats_by_trip.get(t['trip_code'], {}).get('pending_count', 0)}</td>
        <td class="p-3 text-xs text-slate-400">{esc(_fmt_dt(t['created_at']))}</td>
        <td class="p-3 text-xs">
            <a href="/?trip_code={t['trip_code']}" class="text-sky-600 hover:text-sky-800 font-semibold">View Ledger →</a>
        </td>
    </tr>""" for t in all_trips])

    return f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VahanKhata Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True, username=user.get('username', ''), role=user.get('role', ''))}
            <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <table class="w-full text-left">
                    <thead class="bg-slate-50 border-b border-slate-200">
                        <tr>
                            <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Trip Code</th>
                            <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Vehicle</th>
                            <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Driver</th>
                            <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Status</th>
                            <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Advance</th>
                            <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Expenses</th>
                            <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Flagged ₹</th>
                            <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Pending</th>
                            <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Created</th>
                            <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html if all_trips else '<tr><td colspan="10" class="p-6 text-center text-xs text-slate-400">No trips yet.</td></tr>'}
                    </tbody>
                </table>
            </div>
            {render_footer()}
        </div>
    </body>
    </html>"""


@router.get("/", response_class=HTMLResponse)
def index(request: Request, trip_code: str | None = None, new_trip: bool = False):
    guard = require_auth(request)
    if guard is not None:
        return guard
    if not trip_code and not new_trip:
        return RedirectResponse(url="/trips", status_code=303)

    user = get_current_user(request) or {}
    with get_db() as conn:
        all_trips = get_trips_for_user(conn, user.get("user_id"), user.get("role", "super_admin"))
        active_trip = None
        if trip_code:
            candidate = get_trip_by_code(conn, trip_code)
            # Managers/drivers may only open their own trips.
            if candidate and _owns_trip(candidate, user):
                active_trip = candidate
        else:
            active_trip = get_latest_active_trip_for_user(
                conn, user.get("user_id"), user.get("role", "super_admin"))
        if not active_trip and all_trips:
            active_trip = all_trips[0]

        expenses: list[dict] = []
        if active_trip:
            expenses = get_expenses_for_trip(conn, active_trip["trip_code"])

    total_claimed = 0.0
    total_approved = 0.0
    total_income = 0.0
    total_flagged = 0.0
    for e in expenses:
        total_claimed += e["amount"]
        if _is_approved(e) and e["exp_type"] != "GOODS_SALE":
            total_approved += e["amount"]
        if _is_approved(e) and e["exp_type"] == "GOODS_SALE":
            total_income += e["amount"]
        if e["is_flagged"]:
            total_flagged += e["amount"]

    trip_profit = sum(_approved_cash_impact(e) for e in expenses)
    remaining_advance = (active_trip["advance_amount"] + trip_profit) if active_trip else 0.0
    is_trip_settled = bool(active_trip and active_trip["status"] == "SETTLED")
    settled_at_text = (
        esc(_fmt_dt(active_trip["settled_at"]))
        if is_trip_settled and active_trip["settled_at"]
        else "the recorded settlement time"
    )
    settlement_action = (
        f"""<a href="/settle-trip?trip_code={active_trip['trip_code']}" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition shadow">Settle Trip</a>"""
        if active_trip and active_trip["status"] == "ACTIVE"
        else ""
    )

    user = get_current_user(request) or {}

    # Dropdown data for the "Start New Trip" modal: vehicles + active drivers
    # visible to this user (managers see the ones they registered).
    vehicle_options = ""
    driver_options = ""
    if user.get("role") in ("trip_manager", "super_admin"):
        with get_db() as conn:
            vehicles = get_all_vehicles(conn, role=user.get("role", "super_admin"), user_id=user.get("user_id"))
            drivers = get_users_by_roles(conn, ("driver",))
        vehicle_options = "".join(
            f'<option value="{esc(v["vehicle_number"])}" data-id="{v["id"]}">'
            f'{esc(v["vehicle_number"])}{" (" + esc(v["make_model"]) + ")" if v.get("make_model") else ""}</option>'
            for v in vehicles
        )
        driver_options = "".join(
            f'<option value="{esc(d["id"])}" data-name="{esc(d["full_name"])}" '
            f'data-phone="{esc(d["phone"] or "")}">{esc(d["full_name"])}'
            f'{" (" + esc(d["phone"] or "") + ")" if d.get("phone") else ""}</option>'
            for d in drivers
        )

    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VahanKhata End-to-End Working System</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-3 md:p-5 font-sans">
        <div class="max-w-[1500px] mx-auto space-y-4">

            {render_header(authenticated=True, username=user.get('username', ''), role=user.get('role', ''))}

            <div class="flex flex-col lg:flex-row gap-4 items-start">
                {render_sidebar("trips", user.get('role', 'super_admin'))}
                <main class="flex-1 min-w-0 w-full">
                    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">

                <div class="lg:col-span-4 space-y-4">
                    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[750px] lg:h-[calc(100vh-11rem)] lg:min-h-[560px]">

                        <div class="bg-emerald-800 text-white p-3.5 flex items-center justify-between">
                            <div class="flex items-center space-x-2.5">
                                <div class="w-9 h-9 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-sm">🤖</div>
                                <div>
                                    <h3 class="text-sm font-bold leading-tight">VahanKhata Bot (WhatsApp)</h3>
                                    <p class="text-[10px] text-emerald-200">Online • Automated Verification</p>
                                </div>
                            </div>
                            <span class="text-[10px] bg-emerald-900 text-emerald-200 px-2 py-0.5 rounded font-mono">Trip: {esc(active_trip['trip_code']) if active_trip else 'None'}</span>
                        </div>

                        <div class="flex-1 p-4 bg-[#efeae2] overflow-y-auto space-y-3 font-sans text-xs">

                            <div class="bg-white p-3 rounded-lg rounded-tl-none shadow-sm max-w-[85%] space-y-1">
                                <p class="font-bold text-slate-800 text-[11px]">नमस्ते {esc(active_trip['driver_name']) if active_trip else 'Driver'} जी! 👋</p>
                                <p class="text-slate-600">गाड़ी <strong>{esc(active_trip['vehicle_no']) if active_trip else ''}</strong> की ट्रिप <strong>{esc(active_trip['trip_code']) if active_trip else ''}</strong> शुरू हो चुकी है।</p>
                                <p class="text-slate-600">एडवांस जारी: <strong class="text-emerald-700">₹{(active_trip['advance_amount'] if active_trip else 0.0):,.2f}</strong></p>
                                <p class="text-[10px] text-slate-400">डीजल या पर्ची की फोटो यहाँ भेजें।</p>
                            </div>

                            {f'''<div class="bg-emerald-50 border border-emerald-200 p-3 rounded-lg shadow-sm max-w-[85%] text-emerald-900">
                                <p class="font-bold text-[11px]">Trip settled</p>
                                <p class="text-[10px]">This trip was settled on {settled_at_text}. New expenses can no longer be submitted.</p>
                            </div>''' if is_trip_settled else ''}

                            {''.join([f'''
                            <div class="flex flex-col items-end space-y-1">
                                <div class="bg-[#d9fdd3] p-2.5 rounded-lg rounded-tr-none shadow-sm max-w-[85%] text-slate-800">
                                    <p class="font-bold text-[11px]">📸 Logged {esc(e['exp_type'])}: ₹{e['amount']:,.2f}</p>
                                    <p class="text-[10px] text-slate-600">{f"{e['liters']}L @ ₹{e['rate']}/L | Odo: {e['odometer']} KM" if e['exp_type'] in ('FUEL', 'DEF') else f"Odo: {e['odometer']} KM"}</p>
                                </div>
                            </div>

                            <div class="flex flex-col items-start space-y-1">
                                <div class="{'bg-rose-50 border border-rose-200 text-rose-900' if e['is_flagged'] else 'bg-white text-slate-800'} p-2.5 rounded-lg rounded-tl-none shadow-sm max-w-[85%]">
                                    <p class="font-bold text-[11px]">{'⚠️ Anomaly Alert' if e['is_flagged'] else '✅ Verified'}</p>
                                    <p class="text-[10px]">{esc(e['flag_reason']) if e['is_flagged'] else f"₹{e['amount']:,.0f} खर्च दर्ज और सत्यापित हुआ।"}</p>
                                </div>
                            </div>
                            ''' for e in reversed(expenses)])}

                        </div>

                        <div class="p-3 bg-white border-t border-slate-200{' hidden' if is_trip_settled else ''}">
                            <form action="/simulate-whatsapp" method="post" class="space-y-2.5" id="expense-form">
                                <input type="hidden" name="trip_code" value="{esc(active_trip['trip_code']) if active_trip else ''}">

                                <div class="grid grid-cols-2 gap-2">
                                    <div>
                                        <label class="text-[10px] font-bold text-slate-500 block">Type</label>
                                        <select name="exp_type" id="exp_type_select" onchange="ffToggleExpenseFields()" class="w-full text-xs border rounded-lg p-1.5 bg-slate-50 outline-none">
                                            <option value="FUEL">Diesel (डीजल)</option>
                                            <option value="DEF">DEF / AdBlue / यूरिया</option>
                                            <option value="TOLL">Toll (टोल)</option>
                                            <option value="REPAIR">Repair (मरम्मत)</option>
                                            <option value="CHALLAN">Challan (चालान)</option>
                                            <option value="MISC">Misc (विविध)</option>
                                            <option value="GOODS_BUY">Goods Buy (माल खरीद)</option>
                                            <option value="GOODS_SALE">Goods Sale (माल बिक्री)</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label class="text-[10px] font-bold text-slate-500 block">Amount (₹)</label>
                                        <input type="number" step="0.1" name="amount" required placeholder="4500" class="w-full text-xs border rounded-lg p-1.5 bg-slate-50 outline-none">
                                    </div>
                                </div>

                                <div id="odometer-field">
                                    <label class="text-[10px] font-bold text-slate-500 block">Odo (KM)</label>
                                    <input type="number" step="0.1" name="odometer" placeholder="102750" class="w-full text-xs border rounded-lg p-1.5 bg-slate-50 outline-none">
                                </div>

                                <div id="fuel-fields" class="grid grid-cols-2 gap-2">
                                    <div>
                                        <label class="text-[10px] font-bold text-slate-500 block">Liters (Fuel)</label>
                                        <input type="number" step="0.1" name="liters" placeholder="50" class="w-full text-xs border rounded-lg p-1.5 bg-slate-50 outline-none">
                                    </div>
                                    <div>
                                        <label class="text-[10px] font-bold text-slate-500 block">Rate (₹/L)</label>
                                        <input type="number" step="0.1" name="rate" placeholder="90.0" class="w-full text-xs border rounded-lg p-1.5 bg-slate-50 outline-none">
                                    </div>
                                </div>

                                <div id="upload-hint" class="bg-sky-50 border border-sky-200 rounded-lg p-2 text-[10px] text-sky-900"></div>

                                <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2 rounded-xl text-xs transition shadow flex items-center justify-center gap-1.5">
                                    <span>📸</span> Send Expense via WhatsApp
                                </button>
                            </form>
                        </div>

                        <script>
                            const FF_UPLOAD_HINTS = {{
                                FUEL: '📸 Upload: pump receipt/fuel bill + dashboard odometer photo. Used for OCR of volume/rate/amount and mileage (km/L) checks.',
                                DEF: '📸 Upload: DEF/AdBlue pump slip or brand bucket receipt. Verifies vendor authenticity and consumption ratio vs diesel.',
                                REPAIR: '📸 Dual-photo required: mechanic/garage invoice + photo of the replaced/damaged part. Prevents padded labor bills, especially above ₹3,000.',
                                TOLL: '📸 Upload: printed cash toll plaza slip. Proves legitimate cash payment when FASTag failed or on an off-corridor toll road.',
                                CHALLAN: '📸 Upload: official traffic challan/e-challan copy showing offense code and vehicle number.',
                                MISC: '📸 Upload: physical receipt (weighbridge/Dharam Kanta, parking token, entry fee, loading/unloading voucher) for reconciliation.',
                                GOODS_BUY: '📸 Upload: supplier invoice or purchase receipt. This remains pending until the trip manager reviews it.',
                                GOODS_SALE: '📸 Upload: customer invoice or sale receipt. This remains pending until the trip manager reviews it.'
                            }};
                            function ffToggleExpenseFields() {{
                                const type = document.getElementById('exp_type_select').value;
                                const fuelFields = document.getElementById('fuel-fields');
                                const odoField = document.getElementById('odometer-field');
                                const showFuelFields = (type === 'FUEL' || type === 'DEF');
                                fuelFields.style.display = showFuelFields ? 'grid' : 'none';
                                fuelFields.querySelectorAll('input').forEach(i => {{ if (!showFuelFields) i.value = ''; }});
                                const showOdo = (type === 'FUEL' || type === 'REPAIR' || type === 'DEF');
                                odoField.style.display = showOdo ? 'block' : 'none';
                                if (!showOdo) odoField.querySelector('input').value = '';
                                document.getElementById('upload-hint').textContent = FF_UPLOAD_HINTS[type] || '';
                            }}
                            document.addEventListener('DOMContentLoaded', ffToggleExpenseFields);
                        </script>

                    </div>
                </div>

                <div class="lg:col-span-4 space-y-4">
                    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[750px] lg:h-[calc(100vh-11rem)] lg:min-h-[560px]">

                        <div class="bg-amber-800 text-white p-3.5 flex items-center justify-between">
                            <div class="flex items-center space-x-2.5">
                                <div class="w-9 h-9 rounded-full bg-amber-600 flex items-center justify-center font-bold text-sm">👔</div>
                                <div>
                                    <h3 class="text-sm font-bold leading-tight">Fleet Manager (WhatsApp)</h3>
                                    <p class="text-[10px] text-amber-200">Online • Anomaly Escalations</p>
                                </div>
                            </div>
                            <span class="text-[10px] bg-amber-900 text-amber-200 px-2 py-0.5 rounded font-mono">{len([e for e in expenses if (e['is_flagged'] or e['exp_type'] in GOODS_EXPENSE_TYPES) and e['manager_status'] == 'PENDING'])} Pending</span>
                        </div>

                        <div class="flex-1 p-4 bg-[#efeae2] overflow-y-auto space-y-3 font-sans text-xs">

                            <div class="bg-white p-3 rounded-lg rounded-tl-none shadow-sm max-w-[85%] space-y-1">
                                <p class="font-bold text-slate-800 text-[11px]">🔔 Escalation Bot</p>
                                <p class="text-slate-600">Flagged claims and goods transactions on <strong>{esc(active_trip['trip_code']) if active_trip else 'N/A'}</strong> are routed here for owner sign-off.</p>
                            </div>

                            {f'''<div class="bg-emerald-50 border border-emerald-200 p-3 rounded-lg shadow-sm max-w-[85%] text-emerald-900">
                                <p class="font-bold text-[11px]">Trip settled</p>
                                <p class="text-[10px]">This trip was settled on {settled_at_text}. Manager approvals are closed.</p>
                            </div>''' if is_trip_settled else ''}

                            {''.join([f'''
                            <div class="flex flex-col items-start space-y-1">
                                <div class="bg-white border border-amber-200 p-2.5 rounded-lg rounded-tl-none shadow-sm max-w-[90%] text-slate-800">
                                    <p class="font-bold text-[11px] text-rose-700">{'⚠️' if e['is_flagged'] else '📦'} {esc(e['exp_type'])} {'Anomaly' if e['is_flagged'] else 'Review'} — ₹{e['amount']:,.2f}</p>
                                    <p class="text-[10px] text-slate-600">{esc(e['flag_reason']) if e['is_flagged'] else 'Goods transactions require trip manager approval before settlement.'}</p>
                                    <p class="text-[9px] text-slate-400 mt-1">{esc(_fmt_dt(e['created_at']))}</p>
                                </div>
                                {f"""
                                <div class="flex gap-1.5 max-w-[90%]">
                                    <a href='/action-expense?id={e['id']}&action=APPROVE' class='text-[10px] bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-2.5 py-1 rounded-full transition'>✅ Approve</a>
                                    <a href='/action-expense?id={e['id']}&action=REJECT' class='text-[10px] bg-rose-600 hover:bg-rose-700 text-white font-bold px-2.5 py-1 rounded-full transition'>❌ Deduct</a>
                                </div>
                                """ if e['manager_status'] == 'PENDING' else f"""
                                <div class="max-w-[90%]">
                                    <span class="text-[10px] font-bold uppercase {'text-emerald-700' if e['manager_status'] == 'APPROVED' else 'text-rose-700'}">Resolved: {esc(e['manager_status'])}</span>
                                </div>
                                """}
                            </div>
                            ''' for e in expenses if e['is_flagged'] or e['exp_type'] in GOODS_EXPENSE_TYPES]) if any(e['is_flagged'] or e['exp_type'] in GOODS_EXPENSE_TYPES for e in expenses) else '<div class="text-center text-slate-400 text-[11px] pt-6">No reviews pending yet.</div>'}

                        </div>

                        <div class="p-3 bg-white border-t border-slate-200 text-center">
                            <span class="text-[10px] text-slate-400">{'This settled trip is read-only.' if is_trip_settled else 'Approvals here update the Master Ledger in real time.'}</span>
                        </div>

                    </div>
                </div>

                <div class="lg:col-span-4 space-y-4 flex flex-col justify-between">

                    <div class="space-y-4">

                        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                            <div class="flex flex-wrap justify-between items-center gap-2 border-b pb-3">
                                <div>
                                    <div class="flex items-center gap-2">
                                        <h2 class="text-base font-extrabold text-slate-900">{esc(active_trip['trip_code']) if active_trip else 'No Trip'}</h2>
                                        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full {'bg-emerald-100 text-emerald-800' if active_trip and active_trip['status'] == 'ACTIVE' else 'bg-slate-200 text-slate-700'}">
                                            {esc(active_trip['status']) if active_trip else 'N/A'}
                                        </span>
                                    </div>
                                    <p class="text-xs text-slate-500">Vehicle: <strong class="text-slate-800">{esc(active_trip['vehicle_no']) if active_trip else '-'}</strong> | Driver: <strong>{esc(active_trip['driver_name']) if active_trip else '-'}</strong></p>
                                </div>

                                <div class="text-right">
                                    <span class="text-[10px] uppercase font-bold text-slate-400 block">Initial Advance</span>
                                    <span class="text-lg font-black text-slate-900">₹{(active_trip['advance_amount'] if active_trip else 0.0):,.2f}</span>
                                </div>
                            </div>

                            <div class="grid grid-cols-2 gap-2.5 text-center">
                                <div class="bg-slate-50 border border-slate-200 p-2.5 rounded-xl">
                                    <span class="text-[9px] uppercase font-bold text-slate-500 block">Claimed</span>
                                    <span class="text-xs font-bold text-slate-800">₹{total_claimed:,.0f}</span>
                                </div>
                                <div class="bg-slate-50 border border-slate-200 p-2.5 rounded-xl">
                                    <span class="text-[9px] uppercase font-bold text-slate-500 block">Approved Expenses</span>
                                    <span class="text-xs font-bold text-emerald-700">₹{total_approved:,.0f}</span>
                                </div>
                                <div class="bg-rose-50 border border-rose-200 p-2.5 rounded-xl text-rose-700">
                                    <span class="text-[9px] uppercase font-bold block">Flagged</span>
                                    <span class="text-xs font-bold">₹{total_flagged:,.0f}</span>
                                </div>
                                <div class="bg-sky-50 border border-sky-200 p-2.5 rounded-xl text-sky-800">
                                    <span class="text-[9px] uppercase font-bold block">Cash Settlement</span>
                                    <span class="text-xs font-bold">₹{remaining_advance:,.0f}</span>
                                </div>
                                <div class="bg-emerald-50 border border-emerald-200 p-2.5 rounded-xl text-emerald-800 col-span-2">
                                    <span class="text-[9px] uppercase font-bold block">Approved Goods Income</span>
                                    <span class="text-xs font-bold">₹{total_income:,.0f}</span>
                                </div>
                                <div class="{'bg-emerald-50 border-emerald-200 text-emerald-800' if trip_profit >= 0 else 'bg-rose-50 border-rose-200 text-rose-800'} border p-2.5 rounded-xl col-span-2">
                                    <span class="text-[9px] uppercase font-bold block">Net Trip Profit / Loss</span>
                                    <span class="text-xs font-bold">₹{trip_profit:,.2f}</span>
                                </div>
                            </div>
                        </div>

                        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                            <div class="p-4 border-b flex justify-between items-center">
                                <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider">Master Ledger</h3>
                                <span class="text-xs text-slate-400">{len(expenses)} Logs</span>
                            </div>

                            <div class="overflow-x-auto max-h-[360px]">
                                <table class="w-full text-left text-xs">
                                    <thead class="bg-slate-50 text-slate-600 font-semibold border-b text-[11px]">
                                        <tr>
                                            <th class="p-3">Expense</th>
                                            <th class="p-3">Claim</th>
                                            <th class="p-3 text-right">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody class="divide-y divide-slate-100">
                                        {''.join([f'''
                                        <tr class="{'bg-rose-50/60' if e['is_flagged'] and e['manager_status'] == 'PENDING' else 'hover:bg-slate-50'}">
                                            <td class="p-3">
                                                <span class="font-bold text-slate-900 block">{esc(e['exp_type'])}</span>
                                                <span class="text-[10px] text-slate-400">{esc(_fmt_dt(e['created_at']))}</span>
                                            </td>
                                            <td class="p-3">
                                                <span class="font-mono font-bold text-slate-900 block">₹{e['amount']:,.2f}</span>
                                                <span class="text-[10px] text-slate-500">{f"{e['liters']}L @ ₹{e['rate']}/L | Odo: {e['odometer']} KM" if e['exp_type'] in ('FUEL', 'DEF') else f"Odo: {e['odometer']} KM"}</span>
                                            </td>
                                            <td class="p-3 text-right">
                                                {f"<span class='text-[10px] font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded'>PENDING</span>" if e['is_flagged'] and e['manager_status'] == 'PENDING' else f"<span class='text-[10px] font-bold {'bg-emerald-100 text-emerald-800' if e['manager_status'] == 'APPROVED' else 'bg-rose-100 text-rose-800'} px-2 py-0.5 rounded'>{esc(e['manager_status'])}</span>"}
                                            </td>
                                        </tr>
                                        ''' for e in expenses]) if expenses else '<tr><td colspan="3" class="p-6 text-center text-slate-400">No expenses recorded yet. Use the WhatsApp simulator to log receipts.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                    </div>

                    <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex justify-between items-center gap-3">
                        <div>
                            <span class="text-[10px] font-bold uppercase text-slate-400 block">Final Settlement Due</span>
                            <span class="text-base font-black {'text-emerald-700' if remaining_advance >= 0 else 'text-rose-700'}">₹{abs(remaining_advance):,.2f} {'to recover' if remaining_advance >= 0 else 'owner pays'}</span>
                        </div>
                        {settlement_action}
                    </div>

                </div>

                    </div>
                </main>
            </div>
        </div>

        <div id="newTripModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm {'hidden' if not new_trip else ''} flex items-center justify-center p-4 z-50">
            <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
                <div class="border-b pb-3 flex justify-between items-center">
                    <h3 class="font-bold text-slate-900 text-base">Start New Trip & Issue Advance</h3>
                    <button onclick="document.getElementById('newTripModal').classList.add('hidden')" class="text-slate-400 hover:text-slate-600 font-bold">✕</button>
                </div>

                <form action="/create-trip" method="post" class="space-y-3 text-xs">
                    <div>
                        <label class="font-bold text-slate-700 block">Trip Code</label>
                        <input type="text" name="trip_code" required value="TRIP-{datetime.datetime.now().strftime('%M%S')}" class="w-full border rounded-lg p-2 bg-slate-50 font-mono">
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="font-bold text-slate-700 block">Vehicle Number</label>
                            <select name="vehicle_no" id="vehicle_select" required class="w-full border rounded-lg p-2 bg-slate-50" {'' if vehicle_options else 'disabled'}>
                                {f'<option value="">Select vehicle</option>' if vehicle_options else '<option value="">No vehicles registered — add one under Vehicles</option>'}
                                {vehicle_options}
                            </select>
                            <input type="hidden" name="vehicle_id" id="vehicle_id_field">
                        </div>
                        <div>
                            <label class="font-bold text-slate-700 block">Driver</label>
                            <select name="driver_user_id" id="driver_select" required class="w-full border rounded-lg p-2 bg-slate-50" {'' if driver_options else 'disabled'}>
                                {f'<option value="">Select driver</option>' if driver_options else '<option value="">No drivers yet — manage under Drivers</option>'}
                                {driver_options}
                            </select>
                            <input type="hidden" name="driver_name" id="driver_name_field">
                            <input type="hidden" name="driver_phone" id="driver_phone_field">
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="font-bold text-slate-700 block">Trip Advance (₹)</label>
                            <input type="number" step="100" name="advance_amount" required value="25000" class="w-full border rounded-lg p-2 bg-slate-50">
                        </div>
                        <div>
                            <label class="font-bold text-slate-700 block">Start Odometer (KM)</label>
                            <input type="number" step="1" name="start_odo" required value="103500" class="w-full border rounded-lg p-2 bg-slate-50">
                        </div>
                    </div>
                    <div class="pt-2">
                        <div class="flex gap-2">
                            <a href="/trips" class="flex-1 text-center bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-2.5 rounded-xl transition">Cancel</a>
                            <button type="submit" class="flex-1 bg-sky-600 hover:bg-sky-700 text-white font-bold py-2.5 rounded-xl transition shadow" {'' if (vehicle_options and driver_options) else 'disabled'}>
                                🚀 Start Trip & Send WhatsApp Alert
                            </button>
                        </div>
                    </div>
                </form>
                <script>
                    document.getElementById('vehicle_select').addEventListener('change', function () {{
                        document.getElementById('vehicle_id_field').value = this.options[this.selectedIndex].dataset.id || '';
                    }});
                    document.getElementById('driver_select').addEventListener('change', function () {{
                        const opt = this.options[this.selectedIndex];
                        document.getElementById('driver_name_field').value = opt.dataset.name || '';
                        document.getElementById('driver_phone_field').value = opt.dataset.phone || '+91 ';
                    }});
                </script>
            </div>
        </div>

            {render_footer()}
        </div>
    </body>
    </html>"""
    return html
