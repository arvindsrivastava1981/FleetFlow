import os
import io
import sqlite3
import uvicorn
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. Initialize FastAPI App
app = FastAPI(title="FleetFlow Interactive Demo")
DB_FILE = "fleetflow_demo.db"

# 2. Database Helpers
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_code TEXT UNIQUE,
        vehicle_no TEXT,
        driver_name TEXT,
        advance_amount REAL,
        start_odo REAL,
        current_odo REAL,
        status TEXT DEFAULT 'ACTIVE'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_code TEXT,
        exp_type TEXT,
        amount REAL,
        liters REAL,
        rate REAL,
        odometer REAL,
        is_flagged INTEGER DEFAULT 0,
        flag_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Pre-seed default trip if database is empty
    c.execute("SELECT count(*) as count FROM trips")
    if c.fetchone()["count"] == 0:
        c.execute("INSERT INTO trips (trip_code, vehicle_no, driver_name, advance_amount, start_odo, current_odo) VALUES ('TRIP-901', 'UP-93-AT-1234', 'Ramesh Kumar', 25000, 102400, 102400)")
    conn.commit()
    conn.close()

init_db()

# 3. Web Dashboard Route
@app.get("/", response_class=HTMLResponse)
def index():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM trips WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1")
    trip = c.fetchone()
    expenses = []
    total_exp = 0.0
    flagged_count = 0
    if trip:
        c.execute("SELECT * FROM expenses WHERE trip_code = ? ORDER BY id DESC", (trip["trip_code"],))
        expenses = c.fetchall()
        for e in expenses:
            total_exp += e["amount"]
            if e["is_flagged"]:
                flagged_count += 1
    conn.close()
    
    html = f'''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FleetFlow Prototype - Live WhatsApp & Settlement Demo</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-8 font-sans">
        <div class="max-w-6xl mx-auto space-y-6">
            
            <!-- Header -->
            <div class="bg-slate-900 text-white p-6 rounded-xl flex justify-between items-center shadow-md">
                <div>
                    <h1 class="text-2xl font-bold tracking-tight">FleetFlow Working Prototype</h1>
                    <p class="text-sky-400 text-sm font-medium">WhatsApp Expense Verification & Auto-Settlement Engine</p>
                </div>
                <span class="bg-sky-600 text-xs px-3 py-1.5 rounded-full font-bold uppercase tracking-wider">Demo Live</span>
            </div>

            <!-- Two Column Layout -->
            <div class="grid grid-cols-1 md:grid-cols-12 gap-6">
                
                <!-- Left: WhatsApp Driver Simulator -->
                <div class="md:col-span-5 bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
                    <div class="border-b pb-3 flex items-center justify-between">
                        <div class="flex items-center space-x-2">
                            <div class="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                            <h2 class="font-bold text-slate-800">Driver WhatsApp Simulator</h2>
                        </div>
                        <span class="text-xs text-slate-500 font-mono">Trip: {trip['trip_code'] if trip else 'None'}</span>
                    </div>

                    <form action="/simulate-whatsapp" method="post" class="space-y-3">
                        <input type="hidden" name="trip_code" value="{trip['trip_code'] if trip else ''}">
                        
                        <div>
                            <label class="block text-xs font-semibold text-slate-700 uppercase">Expense Category</label>
                            <select name="exp_type" class="w-full mt-1 border rounded-lg p-2 text-sm bg-slate-50 focus:ring-2 focus:ring-sky-500 outline-none">
                                <option value="FUEL">Diesel Fill-up (डीजल पर्ची)</option>
                                <option value="TOLL">Toll Plaza Cash (टोल पर्ची)</option>
                                <option value="REPAIR">Mechanic / Tyre Puncture (मरम्मत)</option>
                            </select>
                        </div>

                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="block text-xs font-semibold text-slate-700 uppercase">Amount (₹)</label>
                                <input type="number" step="0.1" name="amount" required placeholder="e.g. 4500" class="w-full mt-1 border rounded-lg p-2 text-sm bg-slate-50 focus:ring-2 focus:ring-sky-500 outline-none">
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-700 uppercase">Odometer (KM)</label>
                                <input type="number" step="0.1" name="odometer" placeholder="e.g. 102750" class="w-full mt-1 border rounded-lg p-2 text-sm bg-slate-50 focus:ring-2 focus:ring-sky-500 outline-none">
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="block text-xs font-semibold text-slate-700 uppercase">Liters (If Fuel)</label>
                                <input type="number" step="0.1" name="liters" placeholder="e.g. 50" class="w-full mt-1 border rounded-lg p-2 text-sm bg-slate-50 focus:ring-2 focus:ring-sky-500 outline-none">
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-700 uppercase">Rate (₹/L)</label>
                                <input type="number" step="0.1" name="rate" placeholder="e.g. 90.0" class="w-full mt-1 border rounded-lg p-2 text-sm bg-slate-50 focus:ring-2 focus:ring-sky-500 outline-none">
                            </div>
                        </div>

                        <div class="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 space-y-1">
                            <span class="font-bold">Test Fraud Detections:</span>
                            <ul class="list-disc pl-4 space-y-0.5 text-xs">
                                <li>Rate > ₹98/L (Flags price manipulation)</li>
                                <li>Liters > 350L (Flags tank overflow)</li>
                                <li>Low KM jump with high fuel (Flags mileage skim &lt; 2.8 km/L)</li>
                                <li>Toll as cash on FASTag corridors</li>
                            </ul>
                        </div>

                        <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 rounded-lg text-sm transition shadow">
                            📤 Send via WhatsApp Bot (Simulate)
                        </button>
                    </form>
                </div>

                <!-- Right: Fleet Owner Ledger -->
                <div class="md:col-span-7 bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4 flex flex-col justify-between">
                    <div class="space-y-4">
                        <div class="border-b pb-3 flex justify-between items-center">
                            <div>
                                <h2 class="font-bold text-slate-800 text-lg">Active Trip Live Ledger</h2>
                                <p class="text-xs text-slate-500">Vehicle: <strong class="text-slate-800">{trip['vehicle_no']}</strong> | Driver: {trip['driver_name']}</p>
                            </div>
                            <div class="text-right">
                                <span class="text-xs font-semibold uppercase text-slate-400 block">Advance Issued</span>
                                <span class="text-lg font-black text-slate-900">₹{trip['advance_amount']:,.2f}</span>
                            </div>
                        </div>

                        <!-- Metric Cards -->
                        <div class="grid grid-cols-3 gap-3">
                            <div class="p-3 bg-slate-50 border rounded-lg text-center">
                                <span class="text-[10px] uppercase font-bold text-slate-500 block">Total Claimed</span>
                                <span class="text-sm font-bold text-slate-800">₹{total_exp:,.2f}</span>
                            </div>
                            <div class="p-3 bg-slate-50 border rounded-lg text-center">
                                <span class="text-[10px] uppercase font-bold text-slate-500 block">Remaining Cash</span>
                                <span class="text-sm font-bold text-emerald-600">₹{(trip['advance_amount'] - total_exp):,.2f}</span>
                            </div>
                            <div class="p-3 {'bg-rose-50 border-rose-200 text-rose-700' if flagged_count > 0 else 'bg-slate-50 border text-slate-800'} border rounded-lg text-center">
                                <span class="text-[10px] uppercase font-bold block">Red Flags</span>
                                <span class="text-sm font-bold">{flagged_count} Anomalies</span>
                            </div>
                        </div>

                        <!-- Expenses Table -->
                        <div class="overflow-x-auto border rounded-lg">
                            <table class="w-full text-left text-xs">
                                <thead class="bg-slate-100 text-slate-700 uppercase font-semibold border-b">
                                    <tr>
                                        <th class="p-2">Type</th>
                                        <th class="p-2">Amount</th>
                                        <th class="p-2">Details</th>
                                        <th class="p-2">Status</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-slate-100">
                                    {''.join([f'''
                                    <tr class="{'bg-rose-50/70' if e['is_flagged'] else 'hover:bg-slate-50'}">
                                        <td class="p-2 font-bold text-slate-800">{e['exp_type']}</td>
                                        <td class="p-2 font-mono font-bold">₹{e['amount']:,.2f}</td>
                                        <td class="p-2 text-[11px] text-slate-600">
                                            {f"{e['liters']}L @ ₹{e['rate']}/L | Odo: {e['odometer']} KM" if e['exp_type'] == 'FUEL' else f"Odo: {e['odometer']} KM"}
                                        </td>
                                        <td class="p-2">
                                            {f"<span class='text-[10px] font-bold bg-rose-600 text-white px-2 py-0.5 rounded'>{e['flag_reason']}</span>" if e['is_flagged'] else "<span class='text-[10px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded'>VERIFIED</span>"}
                                        </td>
                                    </tr>
                                    ''' for e in expenses]) if expenses else '<tr><td colspan="4" class="p-4 text-center text-slate-400">No expenses logged yet. Submit via simulator.</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Action Buttons -->
                    <div class="pt-4 border-t flex justify-end gap-3">
                        <a href="/reset-demo" class="px-4 py-2 border border-slate-300 text-slate-600 text-xs font-semibold rounded-lg hover:bg-slate-50">Reset Demo</a>
                        <a href="/generate-settlement-pdf" target="_blank" class="bg-sky-600 hover:bg-sky-700 text-white font-bold px-5 py-2 rounded-lg text-xs transition shadow flex items-center gap-2">
                            📄 1-Click Trip Settlement PDF
                        </a>
                    </div>
                </div>

            </div>
        </div>
    </body>
    </html>'''
    return html

# 4. WhatsApp Simulation Endpoint
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
    
    is_flagged = 0
    flag_reason = ""
    
    if exp_type == "FUEL":
        if rate > 98.0 or (rate > 0 and rate < 82.0):
            is_flagged = 1
            flag_reason = f"Unusual rate ₹{rate}/L (Benchmark ₹90.5)"
        elif liters > 350.0:
            is_flagged = 1
            flag_reason = f"Exceeds tank capacity ({liters}L > 350L)"
        else:
            c.execute("SELECT odometer FROM expenses WHERE trip_code = ? AND exp_type = 'FUEL' AND odometer > 0 ORDER BY id DESC LIMIT 1", (trip_code,))
            last_fuel = c.fetchone()
            if last_fuel:
                prev_odo = last_fuel["odometer"]
                if odometer > prev_odo and liters > 0:
                    kml = (odometer - prev_odo) / liters
                    if kml < 2.8:
                        is_flagged = 1
                        flag_reason = f"Low mileage {kml:.1f} km/L (Expected 4.0)"
    elif exp_type == "TOLL":
        is_flagged = 1
        flag_reason = "Cash claimed on FASTag corridor"

    c.execute('''INSERT INTO expenses (trip_code, exp_type, amount, liters, rate, odometer, is_flagged, flag_reason) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                 (trip_code, exp_type, amount, liters, rate, odometer, is_flagged, flag_reason))
    
    if odometer > 0:
        c.execute("UPDATE trips SET current_odo = ? WHERE trip_code = ?", (odometer, trip_code))
        
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

# 5. Reset Demo Endpoint
@app.get("/reset-demo")
def reset_demo():
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM expenses")
    c.execute("UPDATE trips SET current_odo = start_odo WHERE trip_code = 'TRIP-901'")
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

# 6. ReportLab Pure-Python PDF Generation (Windows-Compatible)
@app.get("/generate-settlement-pdf")
def generate_settlement_pdf():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM trips WHERE trip_code = 'TRIP-901'")
    trip = c.fetchone()
    c.execute("SELECT * FROM expenses WHERE trip_code = 'TRIP-901'")
    expenses = c.fetchall()
    conn.close()

    total_approved = sum([e["amount"] for e in expenses if not e["is_flagged"]])
    total_flagged = sum([e["amount"] for e in expenses if e["is_flagged"]])
    net_returnable = trip["advance_amount"] - total_approved

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    # Typography Styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"))
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor("#0284c7"))
    meta_style = ParagraphStyle('MetaStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor("#334155"))
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor("#1e293b"))
    flag_style = ParagraphStyle('FlagStyle', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor("#dc2626"))

    # Header
    story.append(Paragraph("<b>FleetFlow</b>", title_style))
    story.append(Paragraph("Trip Expense Settlement Balance Sheet (Audit-Proof)", sub_style))
    story.append(Spacer(1, 10))

    # Metadata
    odo_dist = trip['current_odo'] - trip['start_odo']
    meta_text = f"<b>Trip:</b> {trip['trip_code']} &nbsp;|&nbsp; <b>Vehicle:</b> {trip['vehicle_no']} &nbsp;|&nbsp; <b>Driver:</b> {trip['driver_name']} &nbsp;|&nbsp; <b>Distance:</b> {odo_dist:,.0f} KM"
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 12))

    # Summary Metrics Table
    summary_data = [
        [
            Paragraph("<b>Advance Issued</b>", cell_style),
            Paragraph("<b>Approved Claims</b>", cell_style),
            Paragraph("<b>Flagged Anomalies</b>", cell_style),
            Paragraph("<b>Driver Due</b>", cell_style)
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
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 15))

    # Expense Breakdown Table
    story.append(Paragraph("<b>Expense Verification Breakdown</b>", styles['Heading3']))
    story.append(Spacer(1, 6))

    table_data = [["Type", "Claimed", "Details", "Audit Status"]]
    for e in expenses:
        details = f"{e['liters']}L @ Rs. {e['rate']}/L (Odo: {e['odometer']} KM)" if e['exp_type'] == 'FUEL' else f"Odo: {e['odometer']} KM"
        status_para = Paragraph(f"<font color='#dc2626'><b>[FLAG]</b> {e['flag_reason']}</font>", flag_style) if e['is_flagged'] else Paragraph("<font color='#16a34a'><b>[VERIFIED]</b></font>", cell_style)
        
        table_data.append([
            Paragraph(f"<b>{e['exp_type']}</b>", cell_style),
            Paragraph(f"Rs. {e['amount']:,.2f}", cell_style),
            Paragraph(details, cell_style),
            status_para
        ])

    if len(table_data) == 1:
        table_data.append([Paragraph("None", cell_style), Paragraph("-", cell_style), Paragraph("No expenses recorded", cell_style), Paragraph("-", cell_style)])

    t_expenses = Table(table_data, colWidths=[65, 80, 200, 175])
    t_expenses.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(t_expenses)

    story.append(Spacer(1, 30))
    sign_data = [["Driver Signature: ___________________", "Fleet Manager Sign-off: ___________________"]]
    t_sign = Table(sign_data, colWidths=[260, 260])
    story.append(t_sign)

    doc.build(story)
    pdf_out = buffer.getvalue()
    buffer.close()

    return Response(content=pdf_out, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=FleetFlow_Settlement.pdf"})

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)