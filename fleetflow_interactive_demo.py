import os
import io
import datetime
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response, RedirectResponse
import uvicorn

# ReportLab for 100% Windows/Linux native PDF generation (No GTK dependencies)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from utils import (
    get_db, fmt_dt, is_admin, render_header, render_footer, render_sidebar,
    evaluate_rules, ADMIN_PASSWORD, ADMIN_COOKIE, _admin_sessions,
    BENCHMARK_PRICE, TANK_CAPACITY, EXPECTED_KML, DEF_RATE_MAX, DEF_MIN_RATIO_PCT, DEF_MAX_RATIO_PCT,
)
import secrets

app = FastAPI(title="FleetFlow Full End-to-End Prototype")

# --- DASHBOARD & ROUTING ---
@app.get("/dashboard", response_class=HTMLResponse)
def savings_dashboard(request: Request):
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT COALESCE(SUM(amount), 0) AS total_claimed,
                        COALESCE(SUM(CASE WHEN manager_status = 'REJECTED' THEN amount ELSE 0 END), 0) AS money_saved,
                        COALESCE(SUM(CASE WHEN manager_status = 'APPROVED' OR (NOT is_flagged AND manager_status != 'REJECTED') THEN amount ELSE 0 END), 0) AS total_approved,
                        COALESCE(SUM(CASE WHEN manager_status = 'PENDING' THEN 1 ELSE 0 END), 0) AS pending_count
                 FROM expenses""")
    totals = c.fetchone()

    c.execute("SELECT COUNT(*) AS trip_count FROM trips")
    trip_count = c.fetchone()["trip_count"]

    # Money saved per trip = flagged claims a manager rejected instead of paying out
    c.execute("""SELECT trip_code,
                        COALESCE(SUM(CASE WHEN manager_status = 'REJECTED' THEN amount ELSE 0 END), 0) AS saved
                 FROM expenses GROUP BY trip_code
                 HAVING COALESCE(SUM(CASE WHEN manager_status = 'REJECTED' THEN amount ELSE 0 END), 0) > 0
                 ORDER BY saved DESC LIMIT 6""")
    savings_by_trip = c.fetchall()
    conn.close()

    money_saved = totals["money_saved"]
    total_claimed = totals["total_claimed"]
    total_approved = totals["total_approved"]
    pending_count = totals["pending_count"]

    chart_labels = [row["trip_code"] for row in savings_by_trip] or ["No rejections yet"]
    chart_values = [row["saved"] for row in savings_by_trip] or [0]

    return f'''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FleetFlow Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True)}
            <div class="flex flex-col lg:flex-row gap-4">
                {render_sidebar("dashboard")}
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
            new Chart(document.getElementById('savingsChart'), {{
                type: 'bar',
                data: {{
                    labels: {chart_labels!r},
                    datasets: [{{
                        label: 'Money saved (₹)',
                        data: {chart_values!r},
                        backgroundColor: '#059669',
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
    </html>'''

@app.get("/trips", response_class=HTMLResponse)
def trip_listing(request: Request):
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM trips ORDER BY CASE WHEN status = 'ACTIVE' THEN 0 ELSE 1 END, id DESC")
    all_trips = c.fetchall()
    c.execute("""SELECT trip_code, COUNT(*) AS expense_count,
                        COALESCE(SUM(amount), 0) AS total_claimed,
                        COALESCE(SUM(CASE WHEN manager_status = 'APPROVED' OR (NOT is_flagged AND manager_status != 'REJECTED') THEN amount ELSE 0 END), 0) AS total_approved,
                        COALESCE(SUM(CASE WHEN manager_status = 'PENDING' THEN 1 ELSE 0 END), 0) AS pending_count
                 FROM expenses GROUP BY trip_code""")
    stats_by_trip = {row["trip_code"]: row for row in c.fetchall()}
    conn.close()

    active_trip = next((trip for trip in all_trips if trip["status"] == "ACTIVE"), None)
    all_trips_settled = not all_trips or all(trip["status"] in ("SETTLED", "CANCELLED") for trip in all_trips)
    trip_rows = ''.join([f'''
        <a href="/?trip_code={trip['trip_code']}" class="block bg-white border {'border-sky-300 ring-2 ring-sky-100' if trip['status'] == 'ACTIVE' else 'border-slate-200'} rounded-2xl p-5 shadow-sm hover:shadow-md transition">
            <div class="flex flex-wrap justify-between gap-3 items-start">
                <div>
                    <div class="flex items-center gap-2">
                        <h2 class="font-extrabold text-slate-900">{trip['trip_code']}</h2>
                        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full {'bg-emerald-100 text-emerald-800' if trip['status'] == 'ACTIVE' else 'bg-slate-200 text-slate-700'}">{trip['status']}</span>
                    </div>
                    <p class="text-xs text-slate-500 mt-1">{trip['vehicle_no']} · {trip['driver_name']}</p>
                </div>
                <span class="text-xs text-sky-700 font-bold">View trip details →</span>
            </div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5 text-xs">
                <div><span class="text-slate-400 block">Advance</span><strong>₹{trip['advance_amount']:,.2f}</strong></div>
                <div><span class="text-slate-400 block">Claims</span><strong>₹{stats_by_trip.get(trip['trip_code'], {}).get('total_claimed', 0):,.2f}</strong></div>
                <div><span class="text-slate-400 block">Approved</span><strong class="text-emerald-700">₹{stats_by_trip.get(trip['trip_code'], {}).get('total_approved', 0):,.2f}</strong></div>
                <div><span class="text-slate-400 block">Pending reviews</span><strong class="text-amber-700">{stats_by_trip.get(trip['trip_code'], {}).get('pending_count', 0)}</strong></div>
            </div>
        </a>''' for trip in all_trips])

    start_trip_control = f'''<a href="/?new_trip=1" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition shadow">➕ Start New Trip</a>''' if all_trips_settled else '''<span class="bg-slate-200 text-slate-400 text-xs font-bold px-4 py-2.5 rounded-xl cursor-not-allowed" title="Settle the current trip before starting another">➕ Start New Trip</span>'''
    return f'''<!DOCTYPE html>
    <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>FleetFlow Trips</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-5xl mx-auto space-y-6">
            {render_header(authenticated=True)}
            <div class="flex items-center justify-between"><div><h2 class="text-lg font-extrabold text-slate-900">All Trips</h2><p class="text-xs text-slate-500">Select a trip to open its complete ledger, audit thread, and settlement details.</p></div>{start_trip_control}<span class="text-xs text-slate-400">{len(all_trips)} total</span></div>
            <div class="space-y-3">{trip_rows if trip_rows else '<div class="bg-white border border-slate-200 rounded-2xl p-10 text-center text-sm text-slate-400">No trips yet. Start your first trip above.</div>'}</div>
            {render_footer()}
        </div>
    </body></html>'''

@app.get("/settled-pdfs", response_class=HTMLResponse)
def settled_pdf_listing(request: Request):
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM trips WHERE status = 'SETTLED' ORDER BY settled_at DESC NULLS LAST, id DESC")
    settled_trips = c.fetchall()
    conn.close()

    pdf_rows = ''.join(f'''
        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div>
                <h2 class="font-extrabold text-slate-900">{trip['trip_code']}</h2>
                <p class="text-xs text-slate-500 mt-1">{trip['vehicle_no']} · {trip['driver_name']}</p>
                <p class="text-[11px] text-slate-400 mt-2">Settled {fmt_dt(trip['settled_at']) if trip['settled_at'] else 'date unavailable'}</p>
            </div>
            <a href="/generate-settlement-pdf?trip_code={trip['trip_code']}" target="_blank" class="bg-sky-600 hover:bg-sky-500 text-white font-bold px-4 py-2.5 rounded-xl text-xs transition shadow flex items-center gap-1.5">
                📄 View Settlement PDF
            </a>
        </div>''' for trip in settled_trips)

    return f'''<!DOCTYPE html>
    <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>FleetFlow Settled PDFs</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True)}
            <div class="flex flex-col lg:flex-row gap-4">
                {render_sidebar("settled-pdfs")}
                <main class="flex-1 space-y-4">
                    <div>
                        <h2 class="text-lg font-extrabold text-slate-900">Settled Trip PDFs</h2>
                        <p class="text-xs text-slate-500">Open settlement reconciliation PDFs for completed trips.</p>
                    </div>
                    <div class="space-y-3">{pdf_rows if pdf_rows else '<div class="bg-white border border-slate-200 rounded-2xl p-10 text-center text-sm text-slate-400">No settled trips yet.</div>'}</div>
                </main>
            </div>
            {render_footer()}
        </div>
    </body></html>'''

@app.get("/fuel-benchmarks", response_class=HTMLResponse)
def fuel_benchmarks_page(request: Request, edit_id: int = None):
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM fuel_benchmarks ORDER BY state_name ASC")
    benchmarks = c.fetchall()
    editing = None
    if edit_id:
        c.execute("SELECT * FROM fuel_benchmarks WHERE id = %s", (edit_id,))
        editing = c.fetchone()
    conn.close()

    rows_html = ''.join([f'''
        <tr class="border-b border-slate-100 hover:bg-slate-50">
            <td class="p-3 text-xs font-bold text-slate-800">{b['state_code']}</td>
            <td class="p-3 text-xs text-slate-600">{b['state_name']}</td>
            <td class="p-3 text-xs text-slate-600">₹{b['benchmark_price_per_liter']:,.2f}</td>
            <td class="p-3 text-xs text-slate-600">{b['tolerance_pct']}%</td>
            <td class="p-3 text-xs text-slate-400">{b['effective_date']}</td>
            <td class="p-3 text-xs flex gap-3">
                <a href="/fuel-benchmarks?edit_id={b['id']}" class="text-sky-600 hover:text-sky-800 font-semibold">Edit</a>
                <a href="/fuel-benchmarks/delete?id={b['id']}" onclick="return confirm('Delete this benchmark?')" class="text-rose-600 hover:text-rose-800 font-semibold">Delete</a>
            </td>
        </tr>''' for b in benchmarks])

    form_action = "/fuel-benchmarks/edit" if editing else "/fuel-benchmarks/add"
    form_title = f"Edit Benchmark: {editing['state_name']}" if editing else "Add New Benchmark"
    id_field = f'<input type="hidden" name="id" value="{editing["id"]}">' if editing else ''
    cancel_link = '<a href="/fuel-benchmarks" class="text-xs text-slate-400 hover:text-slate-600 ml-2">Cancel edit</a>' if editing else ''

    return f'''<!DOCTYPE html>
    <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>FleetFlow Fuel Benchmarks</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True)}
            <div class="flex flex-col lg:flex-row gap-4">
                {render_sidebar("fuel-benchmarks")}
                <main class="flex-1 space-y-4">
                    <div>
                        <h2 class="text-lg font-extrabold text-slate-900">Fuel Benchmarks</h2>
                        <p class="text-xs text-slate-500">State-wise diesel price references used by the rules engine's price-band check.</p>
                    </div>
                    <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                        <h3 class="text-sm font-extrabold text-slate-800 mb-3">{form_title}{cancel_link}</h3>
                        <form action="{form_action}" method="post" class="grid grid-cols-2 md:grid-cols-5 gap-3 items-end">
                            {id_field}
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 block mb-1">State Code</label>
                                <input name="state_code" required maxlength="10" value="{editing['state_code'] if editing else ''}" placeholder="UP" class="w-full text-sm border rounded-lg p-2 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                            </div>
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 block mb-1">State Name</label>
                                <input name="state_name" required maxlength="50" value="{editing['state_name'] if editing else ''}" placeholder="Uttar Pradesh" class="w-full text-sm border rounded-lg p-2 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                            </div>
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 block mb-1">Price ₹/L</label>
                                <input name="benchmark_price_per_liter" type="number" step="0.01" required value="{editing['benchmark_price_per_liter'] if editing else ''}" placeholder="90.50" class="w-full text-sm border rounded-lg p-2 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                            </div>
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 block mb-1">Tolerance %</label>
                                <input name="tolerance_pct" type="number" step="0.01" value="{editing['tolerance_pct'] if editing else '8.0'}" placeholder="8.0" class="w-full text-sm border rounded-lg p-2 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                            </div>
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 block mb-1">Effective Date</label>
                                <input name="effective_date" type="date" value="{editing['effective_date'] if editing else ''}" class="w-full text-sm border rounded-lg p-2 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                            </div>
                            <button type="submit" class="bg-sky-600 hover:bg-sky-500 text-white font-bold px-4 py-2 rounded-xl text-sm transition shadow col-span-2 md:col-span-1">
                                {'Save Changes' if editing else '➕ Add Benchmark'}
                            </button>
                        </form>
                    </div>
                    <div class="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                        <table class="w-full text-left">
                            <thead class="bg-slate-50 border-b border-slate-200">
                                <tr>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Code</th>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">State</th>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Benchmark Price</th>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Tolerance</th>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Effective Date</th>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows_html if benchmarks else '<tr><td colspan="6" class="p-6 text-center text-xs text-slate-400">No fuel benchmarks yet.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </main>
            </div>
            {render_footer()}
        </div>
    </body></html>'''

@app.post("/fuel-benchmarks/add")
def fuel_benchmarks_add(request: Request, state_code: str = Form(...), state_name: str = Form(...),
                         benchmark_price_per_liter: float = Form(...), tolerance_pct: float = Form(8.0),
                         effective_date: str = Form(None)):
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    if effective_date:
        c.execute("""INSERT INTO fuel_benchmarks (state_code, state_name, benchmark_price_per_liter, tolerance_pct, effective_date)
                     VALUES (%s, %s, %s, %s, %s)""",
                  (state_code.strip().upper(), state_name.strip(), benchmark_price_per_liter, tolerance_pct, effective_date))
    else:
        c.execute("""INSERT INTO fuel_benchmarks (state_code, state_name, benchmark_price_per_liter, tolerance_pct)
                     VALUES (%s, %s, %s, %s)""",
                  (state_code.strip().upper(), state_name.strip(), benchmark_price_per_liter, tolerance_pct))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/fuel-benchmarks", status_code=303)

@app.post("/fuel-benchmarks/edit")
def fuel_benchmarks_edit(request: Request, id: int = Form(...), state_code: str = Form(...), state_name: str = Form(...),
                          benchmark_price_per_liter: float = Form(...), tolerance_pct: float = Form(8.0),
                          effective_date: str = Form(None)):
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("""UPDATE fuel_benchmarks
                 SET state_code = %s, state_name = %s, benchmark_price_per_liter = %s,
                     tolerance_pct = %s, effective_date = COALESCE(%s, effective_date)
                 WHERE id = %s""",
              (state_code.strip().upper(), state_name.strip(), benchmark_price_per_liter, tolerance_pct, effective_date, id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/fuel-benchmarks", status_code=303)

@app.get("/fuel-benchmarks/delete")
def fuel_benchmarks_delete(request: Request, id: int):
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM fuel_benchmarks WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/fuel-benchmarks", status_code=303)

@app.get("/rule-engine", response_class=HTMLResponse)
def rule_engine_page(request: Request):
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    def rule_card(exp_type: str, badge_color: str, rules: list[str]) -> str:
        rule_items = ''.join(f'<li class="text-xs text-slate-600 leading-relaxed">{r}</li>' for r in rules)
        return f'''
        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
            <span class="text-[10px] font-bold px-2 py-0.5 rounded-full {badge_color}">{exp_type}</span>
            <ul class="list-disc list-inside mt-3 space-y-1.5">{rule_items}</ul>
        </div>'''

    cards = ''.join([
        rule_card("FUEL", "bg-amber-100 text-amber-800", [
            f"<b>Math integrity:</b> flags if Amount differs from Liters × Rate by more than ₹10.",
            f"<b>Price benchmark:</b> flags if rate is outside ₹82–₹98/L band (base ₹{BENCHMARK_PRICE}/L).",
            f"<b>Tank capacity:</b> flags if claimed liters exceed {TANK_CAPACITY:.0f}L max tank size.",
            f"<b>Odometer rollback:</b> flags if new odometer reading is less than the previous fuel reading.",
            f"<b>Mileage check:</b> flags if calculated km/L falls below 70% of expected {EXPECTED_KML:.1f} km/L (i.e. under 2.8 km/L).",
        ]),
        rule_card("TOLL", "bg-rose-100 text-rose-800", [
            "Always flagged — cash toll claims are disallowed on FASTag-mandated corridors.",
        ]),
        rule_card("REPAIR", "bg-orange-100 text-orange-800", [
            "Flags any repair claim above ₹3,000 as requiring owner pre-approval.",
        ]),
        rule_card("CHALLAN", "bg-rose-100 text-rose-800", [
            "Always flagged — traffic challans must be verified against the e-challan portal.",
        ]),
        rule_card("DEF", "bg-indigo-100 text-indigo-800", [
            f"<b>Price benchmark:</b> flags if DEF/AdBlue rate exceeds ₹{DEF_RATE_MAX:.0f}/L ceiling.",
            f"<b>Consumption ratio:</b> flags if cumulative DEF volume falls outside {DEF_MIN_RATIO_PCT:.0f}–{DEF_MAX_RATIO_PCT:.0f}% of cumulative diesel volume.",
        ]),
        rule_card("RTO-FINE", "bg-rose-100 text-rose-800", [
            "Always flagged — RTO fines always require owner review.",
        ]),
    ])

    return f'''<!DOCTYPE html>
    <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>FleetFlow Rule Engine</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True)}
            <div class="flex flex-col lg:flex-row gap-4">
                {render_sidebar("rule-engine")}
                <main class="flex-1 space-y-4">
                    <div>
                        <h2 class="text-lg font-extrabold text-slate-900">Rule Engine</h2>
                        <p class="text-xs text-slate-500">Automated checks applied to every expense claim via WhatsApp simulation, grouped by expense type.</p>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                        {cards}
                    </div>
                </main>
            </div>
            {render_footer()}
        </div>
    </body></html>'''

@app.get("/", response_class=HTMLResponse)
def index(request: Request, trip_code: str = None, new_trip: bool = False):
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=303)
    if not trip_code and not new_trip:
        return RedirectResponse(url="/trips", status_code=303)

    conn = get_db()
    c = conn.cursor()
    
    # Fetch active trips list
    c.execute("SELECT * FROM trips ORDER BY id DESC")
    all_trips = c.fetchall()
    
    if trip_code:
        c.execute("SELECT * FROM trips WHERE trip_code = %s", (trip_code,))
    else:
        c.execute("SELECT * FROM trips WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1")
    
    active_trip = c.fetchone()
    if not active_trip and all_trips:
        active_trip = all_trips[0]

    expenses = []
    total_claimed = 0.0
    total_approved = 0.0
    total_flagged = 0.0
    
    if active_trip:
        c.execute("SELECT * FROM expenses WHERE trip_code = %s ORDER BY id DESC", (active_trip["trip_code"],))
        expenses = c.fetchall()
        for e in expenses:
            total_claimed += e["amount"]
            if e["manager_status"] == "APPROVED" or (not e["is_flagged"] and e["manager_status"] != "REJECTED"):
                total_approved += e["amount"]
            if e["is_flagged"]:
                total_flagged += e["amount"]

    trip_profit = -total_approved
    remaining_advance = (active_trip["advance_amount"] + trip_profit) if active_trip else 0.0
    pending_expenses = sum(1 for expense in expenses if expense["manager_status"] == "PENDING")
    settlement_action = f'''<a href="/settle-trip?trip_code={active_trip['trip_code']}" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition shadow">Settle Trip</a>''' if active_trip and active_trip["status"] == "ACTIVE" else ''
    conn.close()

    html = f'''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FleetFlow End-to-End Working System</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-3 md:p-5 font-sans">
        <div class="max-w-[1500px] mx-auto space-y-4">
            
            {render_header(authenticated=True)}

            <div class="flex flex-col lg:flex-row gap-4 items-start">
                {render_sidebar("trips")}
                <main class="flex-1 min-w-0 w-full">
                    <!-- Main Workspace Grid: 3-Column Dual-WhatsApp Architecture -->
                    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
                
                <!-- Column 1 (4/12): Driver WhatsApp Simulator -->
                <div class="lg:col-span-4 space-y-4">
                    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[750px] lg:h-[calc(100vh-11rem)] lg:min-h-[560px]">
                        
                        <!-- WhatsApp Header -->
                        <div class="bg-emerald-800 text-white p-3.5 flex items-center justify-between">
                            <div class="flex items-center space-x-2.5">
                                <div class="w-9 h-9 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-sm">🤖</div>
                                <div>
                                    <h3 class="text-sm font-bold leading-tight">FleetFlow Bot (WhatsApp)</h3>
                                    <p class="text-[10px] text-emerald-200">Online • Automated Verification</p>
                                </div>
                            </div>
                            <span class="text-[10px] bg-emerald-900 text-emerald-200 px-2 py-0.5 rounded font-mono">Trip: {active_trip['trip_code'] if active_trip else 'None'}</span>
                        </div>

                        <!-- WhatsApp Chat Feed -->
                        <div class="flex-1 p-4 bg-[#efeae2] overflow-y-auto space-y-3 font-sans text-xs">
                            
                            <!-- Bot Welcome Bubble -->
                            <div class="bg-white p-3 rounded-lg rounded-tl-none shadow-sm max-w-[85%] space-y-1">
                                <p class="font-bold text-slate-800 text-[11px]">नमस्ते {active_trip['driver_name'] if active_trip else 'Driver'} जी! 👋</p>
                                <p class="text-slate-600">गाड़ी <strong>{active_trip['vehicle_no'] if active_trip else ''}</strong> की ट्रिप <strong>{active_trip['trip_code'] if active_trip else ''}</strong> शुरू हो चुकी है।</p>
                                <p class="text-slate-600">एडवांस जारी: <strong class="text-emerald-700">₹{(active_trip['advance_amount'] if active_trip else 0.0):,.2f}</strong></p>
                                <p class="text-[10px] text-slate-400">डीजल या पर्ची की फोटो यहाँ भेजें।</p>
                            </div>

                            <!-- Feed of Logged Transactions as Chat Bubbles -->
                            {''.join([f'''
                            <div class="flex flex-col items-end space-y-1">
                                <div class="bg-[#d9fdd3] p-2.5 rounded-lg rounded-tr-none shadow-sm max-w-[85%] text-slate-800">
                                    <p class="font-bold text-[11px]">📸 Logged {e['exp_type']}: ₹{e['amount']:,.2f}</p>
                                    <p class="text-[10px] text-slate-600">{f"{e['liters']}L @ ₹{e['rate']}/L | Odo: {e['odometer']} KM" if e['exp_type'] in ('FUEL', 'DEF') else f"Odo: {e['odometer']} KM"}</p>
                                </div>
                            </div>
                            
                            <div class="flex flex-col items-start space-y-1">
                                <div class="{'bg-rose-50 border border-rose-200 text-rose-900' if e['is_flagged'] else 'bg-white text-slate-800'} p-2.5 rounded-lg rounded-tl-none shadow-sm max-w-[85%]">
                                    <p class="font-bold text-[11px]">{'⚠️ Anomaly Alert' if e['is_flagged'] else '✅ Verified'}</p>
                                    <p class="text-[10px]">{e['flag_reason'] if e['is_flagged'] else f"₹{e['amount']:,.0f} खर्च दर्ज और सत्यापित हुआ।"}</p>
                                </div>
                            </div>
                            ''' for e in reversed(expenses)])}

                        </div>

                        <!-- Interactive WhatsApp Input Box -->
                        <div class="p-3 bg-white border-t border-slate-200">
                            <form action="/simulate-whatsapp" method="post" class="space-y-2.5" id="expense-form">
                                <input type="hidden" name="trip_code" value="{active_trip['trip_code'] if active_trip else ''}">
                                
                                <div class="grid grid-cols-2 gap-2">
                                    <div>
                                        <label class="text-[10px] font-bold text-slate-500 block">Type</label>
                                        <select name="exp_type" id="exp_type_select" onchange="ffToggleExpenseFields()" class="w-full text-xs border rounded-lg p-1.5 bg-slate-50 outline-none">
                                            <option value="FUEL">Diesel (डीजल)</option>
                                            <option value="DEF">DEF / AdBlue / यूरिया</option>
                                            <option value="TOLL">Toll (टोल)</option>
                                            <option value="REPAIR">Repair (मरम्मत)</option>
                                            <option value="CHALLAN">Challan (चालान)</option>
                                            <option value="RTO-FINE">RTO Fine (आरटीओ जुर्माना)</option>
                                            <option value="OTHER">Other (अन्य)</option>
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
                            // Photo/proof requirement per expense type, shown to the driver before they "send" the claim
                            const FF_UPLOAD_HINTS = {{
                                FUEL: '📸 Upload: pump receipt/fuel bill + dashboard odometer photo. Used for OCR of volume/rate/amount and mileage (km/L) checks.',
                                DEF: '📸 Upload: DEF/AdBlue pump slip or brand bucket receipt. Verifies vendor authenticity and consumption ratio vs diesel.',
                                REPAIR: '📸 Dual-photo required: mechanic/garage invoice + photo of the replaced/damaged part. Prevents padded labor bills, especially above ₹3,000.',
                                TOLL: '📸 Upload: printed cash toll plaza slip. Proves legitimate cash payment when FASTag failed or on an off-corridor toll road.',
                                CHALLAN: '📸 Upload: official traffic challan/e-challan copy showing offense code and vehicle number.',
                                'RTO-FINE': '📸 Upload: official RTO fine slip with offense code, vehicle registration and penalty amount. Validates statutory deductions.',
                                OTHER: '📸 Upload: physical receipt (weighbridge/Dharam Kanta, parking token, entry fee, loading/unloading voucher) for reconciliation.'
                            }};
                            function ffToggleExpenseFields() {{
                                const type = document.getElementById('exp_type_select').value;
                                const fuelFields = document.getElementById('fuel-fields');
                                const odoField = document.getElementById('odometer-field');
                                // Liters/Rate apply to FUEL and DEF claims
                                const showFuelFields = (type === 'FUEL' || type === 'DEF');
                                fuelFields.style.display = showFuelFields ? 'grid' : 'none';
                                fuelFields.querySelectorAll('input').forEach(i => {{ if (!showFuelFields) i.value = ''; }});
                                // Odometer only relevant when tracking vehicle distance (FUEL/REPAIR/DEF)
                                const showOdo = (type === 'FUEL' || type === 'REPAIR' || type === 'DEF');
                                odoField.style.display = showOdo ? 'block' : 'none';
                                if (!showOdo) odoField.querySelector('input').value = '';
                                document.getElementById('upload-hint').textContent = FF_UPLOAD_HINTS[type] || '';
                            }}
                            document.addEventListener('DOMContentLoaded', ffToggleExpenseFields);
                        </script>

                    </div>
                </div>

                <!-- Column 2 (4/12): Manager WhatsApp Escalation Thread -->
                <div class="lg:col-span-4 space-y-4">
                    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[750px] lg:h-[calc(100vh-11rem)] lg:min-h-[560px]">

                        <!-- WhatsApp Header -->
                        <div class="bg-amber-800 text-white p-3.5 flex items-center justify-between">
                            <div class="flex items-center space-x-2.5">
                                <div class="w-9 h-9 rounded-full bg-amber-600 flex items-center justify-center font-bold text-sm">👔</div>
                                <div>
                                    <h3 class="text-sm font-bold leading-tight">Fleet Manager (WhatsApp)</h3>
                                    <p class="text-[10px] text-amber-200">Online • Anomaly Escalations</p>
                                </div>
                            </div>
                            <span class="text-[10px] bg-amber-900 text-amber-200 px-2 py-0.5 rounded font-mono">{len([e for e in expenses if e['is_flagged'] and e['manager_status'] == 'PENDING'])} Pending</span>
                        </div>

                        <!-- Manager Escalation Chat Feed -->
                        <div class="flex-1 p-4 bg-[#efeae2] overflow-y-auto space-y-3 font-sans text-xs">

                            <div class="bg-white p-3 rounded-lg rounded-tl-none shadow-sm max-w-[85%] space-y-1">
                                <p class="font-bold text-slate-800 text-[11px]">🔔 Escalation Bot</p>
                                <p class="text-slate-600">Flagged claims on <strong>{active_trip['trip_code'] if active_trip else 'N/A'}</strong> are routed here for owner sign-off.</p>
                            </div>

                            {''.join([f'''
                            <div class="flex flex-col items-start space-y-1">
                                <div class="bg-white border border-amber-200 p-2.5 rounded-lg rounded-tl-none shadow-sm max-w-[90%] text-slate-800">
                                    <p class="font-bold text-[11px] text-rose-700">⚠️ {e['exp_type']} Anomaly — ₹{e['amount']:,.2f}</p>
                                    <p class="text-[10px] text-slate-600">{e['flag_reason']}</p>
                                    <p class="text-[9px] text-slate-400 mt-1">{fmt_dt(e['created_at'])}</p>
                                </div>
                                {f"""
                                <div class="flex gap-1.5 max-w-[90%]">
                                    <a href='/action-expense?id={e['id']}&action=APPROVE' class='text-[10px] bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-2.5 py-1 rounded-full transition'>✅ Approve</a>
                                    <a href='/action-expense?id={e['id']}&action=REJECT' class='text-[10px] bg-rose-600 hover:bg-rose-700 text-white font-bold px-2.5 py-1 rounded-full transition'>❌ Deduct</a>
                                </div>
                                """ if e['manager_status'] == 'PENDING' else f"""
                                <div class="max-w-[90%]">
                                    <span class="text-[10px] font-bold uppercase {'text-emerald-700' if e['manager_status'] == 'APPROVED' else 'text-rose-700'}">Resolved: {e['manager_status']}</span>
                                </div>
                                """}
                            </div>
                            ''' for e in expenses if e['is_flagged']]) if any(e['is_flagged'] for e in expenses) else '<div class="text-center text-slate-400 text-[11px] pt-6">No anomalies escalated yet.</div>'}

                        </div>

                        <!-- Manager Panel Footer -->
                        <div class="p-3 bg-white border-t border-slate-200 text-center">
                            <span class="text-[10px] text-slate-400">Approvals here update the Master Ledger in real time.</span>
                        </div>

                    </div>
                </div>

                <!-- Column 3 (4/12): Master Ledger -->
                <div class="lg:col-span-4 space-y-4 flex flex-col justify-between">
                    
                    <div class="space-y-4">
                        
                        <!-- Trip Summary Bar -->
                        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                            <div class="flex flex-wrap justify-between items-center gap-2 border-b pb-3">
                                <div>
                                    <div class="flex items-center gap-2">
                                        <h2 class="text-base font-extrabold text-slate-900">{active_trip['trip_code'] if active_trip else 'No Trip'}</h2>
                                        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full {'bg-emerald-100 text-emerald-800' if active_trip and active_trip['status'] == 'ACTIVE' else 'bg-slate-200 text-slate-700'}">
                                            {active_trip['status'] if active_trip else 'N/A'}
                                        </span>
                                    </div>
                                    <p class="text-xs text-slate-500">Vehicle: <strong class="text-slate-800">{active_trip['vehicle_no'] if active_trip else '-'}</strong> | Driver: <strong>{active_trip['driver_name'] if active_trip else '-'}</strong></p>
                                </div>

                                <div class="text-right">
                                    <span class="text-[10px] uppercase font-bold text-slate-400 block">Initial Advance</span>
                                    <span class="text-lg font-black text-slate-900">₹{(active_trip['advance_amount'] if active_trip else 0.0):,.2f}</span>
                                </div>
                            </div>

                            <!-- Financial Metrics Grid -->
                            <div class="grid grid-cols-2 gap-2.5 text-center">
                                <div class="bg-slate-50 border border-slate-200 p-2.5 rounded-xl">
                                    <span class="text-[9px] uppercase font-bold text-slate-500 block">Claimed</span>
                                    <span class="text-xs font-bold text-slate-800">₹{total_claimed:,.0f}</span>
                                </div>
                                <div class="bg-slate-50 border border-slate-200 p-2.5 rounded-xl">
                                    <span class="text-[9px] uppercase font-bold text-slate-500 block">Approved</span>
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
                                <div class="{'bg-emerald-50 border-emerald-200 text-emerald-800' if trip_profit >= 0 else 'bg-rose-50 border-rose-200 text-rose-800'} border p-2.5 rounded-xl col-span-2">
                                    <span class="text-[9px] uppercase font-bold block">Net Trip Profit / Loss</span>
                                    <span class="text-xs font-bold">₹{trip_profit:,.2f}</span>
                                </div>
                            </div>
                        </div>

                        <!-- Master Ledger Table (read-only view; approvals happen in the Manager column) -->
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
                                                <span class="font-bold text-slate-900 block">{e['exp_type']}</span>
                                                <span class="text-[10px] text-slate-400">{fmt_dt(e['created_at'])}</span>
                                            </td>
                                            <td class="p-3">
                                                <span class="font-mono font-bold text-slate-900 block">₹{e['amount']:,.2f}</span>
                                                <span class="text-[10px] text-slate-500">{f"{e['liters']}L @ ₹{e['rate']}/L | Odo: {e['odometer']} KM" if e['exp_type'] in ('FUEL', 'DEF') else f"Odo: {e['odometer']} KM"}</span>
                                            </td>
                                            <td class="p-3 text-right">
                                                {f"<span class='text-[10px] font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded'>PENDING</span>" if e['is_flagged'] and e['manager_status'] == 'PENDING' else f"<span class='text-[10px] font-bold {'bg-emerald-100 text-emerald-800' if e['manager_status'] == 'APPROVED' else 'bg-rose-100 text-rose-800'} px-2 py-0.5 rounded'>{e['manager_status']}</span>"}
                                            </td>
                                        </tr>
                                        ''' for e in expenses]) if expenses else '<tr><td colspan="3" class="p-6 text-center text-slate-400">No expenses recorded yet. Use the WhatsApp simulator to log receipts.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                    </div>

                    <!-- Bottom Action Bar -->
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

        <!-- Modal: Start New Trip -->
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
                            <input type="text" name="vehicle_no" required value="UP-93-AT-1234" class="w-full border rounded-lg p-2 bg-slate-50">
                        </div>
                        <div>
                            <label class="font-bold text-slate-700 block">Driver Name</label>
                            <input type="text" name="driver_name" required placeholder="e.g. Ramesh Kumar" class="w-full border rounded-lg p-2 bg-slate-50">
                        </div>
                    </div>
                    <div>
                        <label class="font-bold text-slate-700 block">Driver Phone</label>
                        <input type="text" name="driver_phone" required value="+91 90000 00000" class="w-full border rounded-lg p-2 bg-slate-50">
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
                            <button type="submit" class="flex-1 bg-sky-600 hover:bg-sky-700 text-white font-bold py-2.5 rounded-xl transition shadow">
                                🚀 Start Trip & Send WhatsApp Alert
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>

            {render_footer()}
        </div>
    </body>
    </html>'''
    return html

# --- BACKEND SIMULATION ACTIONS ---

@app.post("/create-trip")
def create_trip(
    trip_code: str = Form(...),
    vehicle_no: str = Form(...),
    driver_name: str = Form(...),
    driver_phone: str = Form("+91 90000 00000"),
    advance_amount: float = Form(...),
    start_odo: float = Form(...)
):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT 1 FROM trips WHERE status = 'ACTIVE' LIMIT 1")
    if c.fetchone():
        conn.close()
        return RedirectResponse(url="/trips", status_code=303)
    c.execute('''INSERT INTO trips (trip_code, vehicle_no, driver_name, driver_phone, advance_amount, start_odo, current_odo, status)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE')''',
                 (trip_code, vehicle_no, driver_name, driver_phone, advance_amount, start_odo, start_odo))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)

@app.post("/simulate-whatsapp")
def simulate_whatsapp(
    trip_code: str = Form(...),
    exp_type: str = Form(...),
    amount: float = Form(...),
    odometer: float = Form(0.0),
    liters: float = Form(0.0),
    rate: float = Form(0.0)
):
    conn = get_db()
    c = conn.cursor()
    
    # Run through the multi-layer rules engine
    is_flagged, flag_reason = evaluate_rules(trip_code, exp_type, amount, liters, rate, odometer)
    manager_status = "PENDING" if is_flagged else "APPROVED"

    c.execute('''INSERT INTO expenses (trip_code, exp_type, amount, liters, rate, odometer, is_flagged, flag_reason, manager_status) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''', 
                 (trip_code, exp_type, amount, liters, rate, odometer, is_flagged, flag_reason, manager_status))
    
    # Update current vehicle odometer
    if odometer > 0:
        c.execute("UPDATE trips SET current_odo = GREATEST(current_odo, %s) WHERE trip_code = %s", (odometer, trip_code))
        
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)

@app.get("/action-expense")
def action_expense(id: int, action: str):
    conn = get_db()
    c = conn.cursor()
    status = "APPROVED" if action == "APPROVE" else "REJECTED"
    c.execute("UPDATE expenses SET manager_status = %s WHERE id = %s", (status, id))
    
    # Fetch trip code for redirect
    c.execute("SELECT trip_code FROM expenses WHERE id = %s", (id,))
    row = c.fetchone()
    trip_code = row["trip_code"] if row else ""
    
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)

@app.get("/settle-trip")
def settle_trip(request: Request, trip_code: str):
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) AS pending_count FROM expenses WHERE trip_code = %s AND manager_status = 'PENDING'", (trip_code,))
    pending_count = c.fetchone()["pending_count"]
    if pending_count:
        conn.close()
        return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)

    c.execute("""UPDATE trips
                 SET status = 'SETTLED', end_odo = current_odo,
                     completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP),
                     settled_at = CURRENT_TIMESTAMP
                 WHERE trip_code = %s AND status = 'ACTIVE'""", (trip_code,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/trips", status_code=303)

@app.get("/reset-demo")
def reset_demo():
    # Clears transactional data only; schema/tables and seed data are managed manually in Neon
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM expenses")
    c.execute("DELETE FROM trips")
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

# --- ADMIN LOGIN & DASHBOARD ---
@app.get("/login", response_class=HTMLResponse)
def admin_login_form(error: str = None):
    return f'''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FleetFlow Admin Login</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-5xl mx-auto space-y-6">
            {render_header(authenticated=False)}
            <main class="min-h-[60vh] flex items-center justify-center">
            <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 w-full max-w-sm space-y-5">
            <div class="text-center space-y-1">
                <div class="bg-sky-500 inline-block p-2 rounded-xl text-white font-black text-xl">FF</div>
                <h1 class="text-lg font-extrabold text-slate-800">Admin Login</h1>
                <p class="text-xs text-slate-500">Enter the admin password to continue</p>
            </div>
            {'<p class="text-xs text-rose-600 font-semibold text-center">Incorrect password. Try again.</p>' if error else ''}
            <form action="/login" method="post" class="space-y-3">
                <input type="password" name="password" required autofocus placeholder="Password"
                       class="w-full text-sm border rounded-lg p-2.5 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                <button type="submit" class="w-full bg-sky-600 hover:bg-sky-500 text-white font-bold py-2.5 rounded-xl text-sm transition shadow">
                    Login
                </button>
            </form>            
            </div>
            </main>
            {render_footer()}
        </div>
    </body>
    </html>'''

@app.post("/login")
def admin_login_submit(password: str = Form(...)):
    if password != ADMIN_PASSWORD:
        return RedirectResponse(url="/login?error=1", status_code=303)
    token = secrets.token_urlsafe(32)
    _admin_sessions.add(token)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key=ADMIN_COOKIE, value=token, httponly=True, samesite="lax", max_age=60 * 60 * 12)
    return response

@app.get("/logout")
def admin_logout(request: Request):
    token = request.cookies.get(ADMIN_COOKIE)
    _admin_sessions.discard(token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(ADMIN_COOKIE)
    return response

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM trips ORDER BY id DESC")
    all_trips = c.fetchall()

    c.execute('''SELECT trip_code,
                        COUNT(*) AS expense_count,
                        COALESCE(SUM(amount), 0) AS total_amount,
                        COALESCE(SUM(CASE WHEN is_flagged THEN amount ELSE 0 END), 0) AS flagged_amount,
                        COALESCE(SUM(CASE WHEN manager_status = 'PENDING' THEN 1 ELSE 0 END), 0) AS pending_count
                 FROM expenses GROUP BY trip_code''')
    stats_by_trip = {row["trip_code"]: row for row in c.fetchall()}
    conn.close()

    rows_html = ''.join([f'''
    <tr class="border-b border-slate-100 hover:bg-slate-50">
        <td class="p-3 text-xs font-bold text-slate-800">{t['trip_code']}</td>
        <td class="p-3 text-xs text-slate-600">{t['vehicle_no']}</td>
        <td class="p-3 text-xs text-slate-600">{t['driver_name']}</td>
        <td class="p-3 text-xs">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold {'bg-emerald-100 text-emerald-700' if t['status'] == 'ACTIVE' else 'bg-slate-200 text-slate-600'}">{t['status']}</span>
        </td>
        <td class="p-3 text-xs text-slate-600">₹{t['advance_amount']:,.2f}</td>
        <td class="p-3 text-xs text-slate-600">{stats_by_trip.get(t['trip_code'], {}).get('expense_count', 0)}</td>
        <td class="p-3 text-xs text-rose-600 font-semibold">₹{stats_by_trip.get(t['trip_code'], {}).get('flagged_amount', 0):,.2f}</td>
        <td class="p-3 text-xs text-amber-600 font-semibold">{stats_by_trip.get(t['trip_code'], {}).get('pending_count', 0)}</td>
        <td class="p-3 text-xs text-slate-400">{fmt_dt(t['created_at'])}</td>
        <td class="p-3 text-xs">
            <a href="/?trip_code={t['trip_code']}" class="text-sky-600 hover:text-sky-800 font-semibold">View Ledger →</a>
        </td>
    </tr>''' for t in all_trips])

    return f'''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FleetFlow Admin</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True)}

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
    </html>'''

# --- 1-CLICK SETTLEMENT PDF GENERATOR ---
@app.get("/generate-settlement-pdf")
def generate_settlement_pdf(trip_code: str = "TRIP-101"):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM trips WHERE trip_code = %s", (trip_code,))
    trip = c.fetchone()
    c.execute("SELECT * FROM expenses WHERE trip_code = %s ORDER BY id ASC", (trip_code,))
    expenses = c.fetchall()
    conn.close()

    if not trip:
        return Response("Trip not found", status_code=404)

    total_approved = sum([e["amount"] for e in expenses if e["manager_status"] == "APPROVED" or (not e["is_flagged"] and e["manager_status"] != "REJECTED")])
    total_flagged = sum([e["amount"] for e in expenses if e["is_flagged"]])
    trip_profit = -total_approved
    net_returnable = trip["advance_amount"] + trip_profit

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"))
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor("#0284c7"))
    meta_style = ParagraphStyle('MetaStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor("#334155"))
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor("#1e293b"))
    flag_style = ParagraphStyle('FlagStyle', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor("#dc2626"))

    # Header
    story.append(Paragraph("<b>FleetFlow</b>", title_style))
    story.append(Paragraph("Official Trip Settlement & Advance Reconciliation Ledger", sub_style))
    story.append(Spacer(1, 10))

    # Metadata
    odo_dist = trip['current_odo'] - trip['start_odo']
    meta_text = f"<b>Trip Code:</b> {trip['trip_code']} &nbsp;|&nbsp; <b>Vehicle No:</b> {trip['vehicle_no']} &nbsp;|&nbsp; <b>Driver:</b> {trip['driver_name']} &nbsp;|&nbsp; <b>Distance Run:</b> {odo_dist:,.0f} KM"
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 12))

    # Settlement Summary Grid
    summary_data = [
        [
            Paragraph("<b>Advance Issued</b>", cell_style),
            Paragraph("<b>Approved Claims</b>", cell_style),
            Paragraph("<b>Flagged Deductions</b>", cell_style),
            Paragraph("<b>Cash Settlement</b>", cell_style)
        ],
        [
            Paragraph(f"<b>Rs. {trip['advance_amount']:,.2f}</b>", cell_style),
            Paragraph(f"<b>Rs. {total_approved:,.2f}</b>", cell_style),
            Paragraph(f"<font color='#dc2626'><b>Rs. {total_flagged:,.2f}</b></font>", cell_style),
            Paragraph(f"<font color='#16a34a'><b>Rs. {net_returnable:,.2f}</b></font>", cell_style)
        ]
    ]
    t_summary = Table(summary_data, colWidths=[130, 130, 130, 130])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 15))

    # Itemized Breakdown Table
    story.append(Paragraph("<b>Itemized Expense Audit Trail</b>", styles['Heading3']))
    story.append(Spacer(1, 6))

    table_data = [["Expense", "Claim Amount", "Operational Metrics", "Audit Verification", "Status"]]
    for e in expenses:
        details = f"{e['liters']}L @ Rs. {e['rate']}/L (Odo: {e['odometer']} KM)" if e['exp_type'] in ('FUEL', 'DEF') else f"Odo: {e['odometer']} KM"
        audit_para = Paragraph(f"<font color='#dc2626'><b>[FLAG]</b> {e['flag_reason']}</font>", flag_style) if e['is_flagged'] else Paragraph("<font color='#16a34a'><b>[VERIFIED]</b></font>", cell_style)
        
        table_data.append([
            Paragraph(f"<b>{e['exp_type']}</b>", cell_style),
            Paragraph(f"Rs. {e['amount']:,.2f}", cell_style),
            Paragraph(details, cell_style),
            audit_para,
            Paragraph(f"<b>{e['manager_status']}</b>", cell_style)
        ])

    t_expenses = Table(table_data, colWidths=[60, 75, 170, 150, 65])
    t_expenses.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(t_expenses)

    story.append(Paragraph(f"<b>Net trip profit / loss after approved expenses:</b> Rs. {trip_profit:,.2f}", meta_style))

    # Signatures
    story.append(Spacer(1, 35))
    sign_data = [["Driver Signature: ___________________", "Fleet Manager Sign-off: ___________________"]]
    t_sign = Table(sign_data, colWidths=[260, 260])
    story.append(t_sign)

    doc.build(story)
    pdf_out = buffer.getvalue()
    buffer.close()

    return Response(content=pdf_out, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename={trip_code}_Settlement.pdf"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))