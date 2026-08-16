import os
import io
import sqlite3
import datetime
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response, RedirectResponse
import uvicorn

# ReportLab for 100% Windows/Linux native PDF generation (No GTK dependencies)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = FastAPI(title="FleetFlow Full End-to-End Prototype")
DB_FILE = "fleetflow_demo.db"

# --- DATABASE SETUP ---
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # 1. Trips table
    c.execute('''CREATE TABLE IF NOT EXISTS trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_code TEXT UNIQUE,
        vehicle_no TEXT,
        driver_name TEXT,
        driver_phone TEXT,
        advance_amount REAL,
        start_odo REAL,
        current_odo REAL,
        status TEXT DEFAULT 'ACTIVE', -- ACTIVE / SETTLED
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        settled_at TIMESTAMP
    )''')
    
    # 2. Expenses table
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_code TEXT,
        exp_type TEXT,
        amount REAL,
        liters REAL,
        rate REAL,
        odometer REAL,
        station_name TEXT,
        is_flagged INTEGER DEFAULT 0,
        flag_reason TEXT,
        manager_status TEXT DEFAULT 'PENDING', -- PENDING / APPROVED / REJECTED
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Migration helper: ensure new columns exist in older database files
    try:
        c.execute("ALTER TABLE expenses ADD COLUMN manager_status TEXT DEFAULT 'PENDING'")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE expenses ADD COLUMN station_name TEXT")
    except sqlite3.OperationalError:
        pass

    # Pre-seed initial demo trip if database is empty
    c.execute("SELECT count(*) as count FROM trips")
    if c.fetchone()["count"] == 0:
        c.execute('''INSERT INTO trips 
                     (trip_code, vehicle_no, driver_name, driver_phone, advance_amount, start_odo, current_odo, status) 
                     VALUES ('TRIP-101', 'UP-93-AT-1234', 'Ramesh Kumar', '+91 98765 43210', 25000, 102400, 102400, 'ACTIVE')''')
        
        # Pre-seed sample transactions
        c.execute('''INSERT INTO expenses (trip_code, exp_type, amount, liters, rate, odometer, station_name, is_flagged, flag_reason, manager_status) 
                     VALUES ('TRIP-101', 'FUEL', 4500, 50, 90.0, 102600, 'Indian Oil Highway Pump', 0, '', 'APPROVED')''')
        c.execute('''INSERT INTO expenses (trip_code, exp_type, amount, liters, rate, odometer, station_name, is_flagged, flag_reason, manager_status) 
                     VALUES ('TRIP-101', 'TOLL', 850, 0, 0, 102750, 'NH-19 Toll Plaza', 1, 'Cash claimed on 100% FASTag corridor', 'PENDING')''')
        c.execute('''INSERT INTO expenses (trip_code, exp_type, amount, liters, rate, odometer, station_name, is_flagged, flag_reason, manager_status) 
                     VALUES ('TRIP-101', 'FUEL', 5400, 60, 90.0, 102850, 'HPCL Fuel Stop', 1, 'Low mileage 1.7 km/L (Expected ~4.0 km/L)', 'PENDING')''')
    
    conn.commit()
    conn.close()

init_db()

# --- MULTI-LAYER RULES ENGINE ---
BENCHMARK_PRICE = 90.50 # State diesel price baseline (₹/L)
TANK_CAPACITY = 350.0   # Max tank capacity in Liters
EXPECTED_KML = 4.0      # Expected mileage (km/L)

def evaluate_rules(trip_code: str, exp_type: str, amount: float, liters: float, rate: float, odo: float) -> tuple[int, str]:
    conn = get_db()
    c = conn.cursor()
    
    is_flagged = 0
    flag_reason = ""
    
    if exp_type == "FUEL":
        # Rule 1: Math integrity check (Amount == Liters * Rate)
        if liters > 0 and rate > 0:
            calc_amt = liters * rate
            if abs(amount - calc_amt) > 10.0:
                is_flagged = 1
                flag_reason = f"Math Mismatch: Claimed ₹{amount:,.0f} vs {liters}L @ ₹{rate}/L = ₹{calc_amt:,.0f}"

        # Rule 2: Price benchmark check (₹82 - ₹98/L)
        if not is_flagged and (rate > 98.0 or (rate > 0 and rate < 82.0)):
            is_flagged = 1
            flag_reason = f"Rate ₹{rate}/L outside benchmark band (₹83 - ₹98)"

        # Rule 3: Tank overflow check (> 350L)
        elif not is_flagged and liters > TANK_CAPACITY:
            is_flagged = 1
            flag_reason = f"Quantity {liters}L exceeds max tank capacity ({TANK_CAPACITY}L)"

        # Rule 4: Odometer rollback and mileage delta check
        elif not is_flagged and odo > 0:
            c.execute("SELECT odometer FROM expenses WHERE trip_code = ? AND exp_type = 'FUEL' AND odometer > 0 ORDER BY id DESC LIMIT 1", (trip_code,))
            last_fuel = c.fetchone()
            
            if last_fuel:
                prev_odo = last_fuel["odometer"]
            else:
                c.execute("SELECT start_odo FROM trips WHERE trip_code = ?", (trip_code,))
                t_row = c.fetchone()
                prev_odo = t_row["start_odo"] if t_row else 0.0

            if prev_odo > 0 and odo < prev_odo:
                is_flagged = 1
                flag_reason = f"Odometer rollback ({odo:,.0f} KM < previous {prev_odo:,.0f} KM)"
            elif prev_odo > 0 and odo > prev_odo and liters > 0:
                calc_kml = (odo - prev_odo) / liters
                if calc_kml < (EXPECTED_KML * 0.70): # Below 2.8 km/L
                    is_flagged = 1
                    flag_reason = f"Abnormal mileage {calc_kml:.1f} km/L (Expected ~{EXPECTED_KML:.1f} km/L)"

    elif exp_type == "TOLL":
        is_flagged = 1
        flag_reason = "Cash claimed on FASTag-mandated corridor"

    elif exp_type == "REPAIR":
        if amount > 3000.0:
            is_flagged = 1
            flag_reason = "Major repair > ₹3,000 requires owner pre-approval"

    conn.close()
    return is_flagged, flag_reason

# --- DASHBOARD & ROUTING ---
@app.get("/", response_class=HTMLResponse)
def index(trip_code: str = None):
    conn = get_db()
    c = conn.cursor()
    
    # Fetch active trips list
    c.execute("SELECT * FROM trips ORDER BY id DESC")
    all_trips = c.fetchall()
    
    if trip_code:
        c.execute("SELECT * FROM trips WHERE trip_code = ?", (trip_code,))
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
        c.execute("SELECT * FROM expenses WHERE trip_code = ? ORDER BY id DESC", (active_trip["trip_code"],))
        expenses = c.fetchall()
        for e in expenses:
            total_claimed += e["amount"]
            if e["manager_status"] == "APPROVED" or (not e["is_flagged"] and e["manager_status"] != "REJECTED"):
                total_approved += e["amount"]
            if e["is_flagged"]:
                total_flagged += e["amount"]
                
    remaining_advance = (active_trip["advance_amount"] - total_approved) if active_trip else 0.0
    conn.close()

    html = f'''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FleetFlow End-to-End Working System</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            
            <!-- Top Navbar -->
            <div class="bg-slate-900 text-white p-5 rounded-2xl flex flex-wrap justify-between items-center shadow-lg gap-4">
                <div class="flex items-center space-x-3">
                    <div class="bg-sky-500 p-2 rounded-xl text-white font-black text-xl">FF</div>
                    <div>
                        <h1 class="text-xl font-extrabold tracking-tight">FleetFlow</h1>
                        <p class="text-xs text-sky-400 font-medium">Real-Time Expense Verification & Settlement Engine</p>
                    </div>
                </div>
                
                <div class="flex items-center gap-3">
                    <button onclick="document.getElementById('newTripModal').classList.remove('hidden')" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold px-4 py-2 rounded-xl transition shadow flex items-center gap-1.5">
                        ➕ Start New Trip
                    </button>
                    <a href="/reset-demo" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-3 py-2 rounded-xl transition">
                        🔄 Reset Demo
                    </a>
                </div>
            </div>

            <!-- Main Workspace Grid -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                
                <!-- Left 5 Columns: WhatsApp Driver Simulator Phone -->
                <div class="lg:col-span-5 space-y-4">
                    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[750px]">
                        
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
                                <p class="text-slate-600">एडवांस जारी: <strong class="text-emerald-700">₹{active_trip['advance_amount']:,.2f}</strong></p>
                                <p class="text-[10px] text-slate-400">डीजल या पर्ची की फोटो यहाँ भेजें।</p>
                            </div>

                            <!-- Feed of Logged Transactions as Chat Bubbles -->
                            {''.join([f'''
                            <div class="flex flex-col items-end space-y-1">
                                <div class="bg-[#d9fdd3] p-2.5 rounded-lg rounded-tr-none shadow-sm max-w-[85%] text-slate-800">
                                    <p class="font-bold text-[11px]">📸 Logged {e['exp_type']}: ₹{e['amount']:,.2f}</p>
                                    <p class="text-[10px] text-slate-600">{f"{e['liters']}L @ ₹{e['rate']}/L | Odo: {e['odometer']} KM" if e['exp_type'] == 'FUEL' else f"Odo: {e['odometer']} KM"}</p>
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
                            <form action="/simulate-whatsapp" method="post" class="space-y-2.5">
                                <input type="hidden" name="trip_code" value="{active_trip['trip_code'] if active_trip else ''}">
                                
                                <div class="grid grid-cols-3 gap-2">
                                    <div>
                                        <label class="text-[10px] font-bold text-slate-500 block">Type</label>
                                        <select name="exp_type" class="w-full text-xs border rounded-lg p-1.5 bg-slate-50 outline-none">
                                            <option value="FUEL">Diesel (डीजल)</option>
                                            <option value="TOLL">Toll (टोल)</option>
                                            <option value="REPAIR">Repair (मरम्मत)</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label class="text-[10px] font-bold text-slate-500 block">Amount (₹)</label>
                                        <input type="number" step="0.1" name="amount" required placeholder="4500" class="w-full text-xs border rounded-lg p-1.5 bg-slate-50 outline-none">
                                    </div>
                                    <div>
                                        <label class="text-[10px] font-bold text-slate-500 block">Odo (KM)</label>
                                        <input type="number" step="0.1" name="odometer" placeholder="102750" class="w-full text-xs border rounded-lg p-1.5 bg-slate-50 outline-none">
                                    </div>
                                </div>

                                <div class="grid grid-cols-2 gap-2">
                                    <div>
                                        <label class="text-[10px] font-bold text-slate-500 block">Liters (Fuel)</label>
                                        <input type="number" step="0.1" name="liters" placeholder="50" class="w-full text-xs border rounded-lg p-1.5 bg-slate-50 outline-none">
                                    </div>
                                    <div>
                                        <label class="text-[10px] font-bold text-slate-500 block">Rate (₹/L)</label>
                                        <input type="number" step="0.1" name="rate" placeholder="90.0" class="w-full text-xs border rounded-lg p-1.5 bg-slate-50 outline-none">
                                    </div>
                                </div>

                                <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2 rounded-xl text-xs transition shadow flex items-center justify-center gap-1.5">
                                    <span>📸</span> Send Expense via WhatsApp
                                </button>
                            </form>
                        </div>

                    </div>
                </div>

                <!-- Right 7 Columns: Live Fleet Manager Ledger -->
                <div class="lg:col-span-7 space-y-4 flex flex-col justify-between">
                    
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
                            <div class="grid grid-cols-4 gap-2.5 text-center">
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
                                    <span class="text-[9px] uppercase font-bold block">Cash in Hand</span>
                                    <span class="text-xs font-bold">₹{remaining_advance:,.0f}</span>
                                </div>
                            </div>
                        </div>

                        <!-- Live Verification Ledger Table -->
                        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                            <div class="p-4 border-b flex justify-between items-center">
                                <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider">Live Expense Verification & Manager Controls</h3>
                                <span class="text-xs text-slate-400">{len(expenses)} Logs</span>
                            </div>

                            <div class="overflow-x-auto max-h-[360px]">
                                <table class="w-full text-left text-xs">
                                    <thead class="bg-slate-50 text-slate-600 font-semibold border-b text-[11px]">
                                        <tr>
                                            <th class="p-3">Expense</th>
                                            <th class="p-3">Claim</th>
                                            <th class="p-3">Audit Rule Flag</th>
                                            <th class="p-3 text-right">Manager Action</th>
                                        </tr>
                                    </thead>
                                    <tbody class="divide-y divide-slate-100">
                                        {''.join([f'''
                                        <tr class="{'bg-rose-50/60' if e['is_flagged'] and e['manager_status'] == 'PENDING' else 'hover:bg-slate-50'}">
                                            <td class="p-3">
                                                <span class="font-bold text-slate-900 block">{e['exp_type']}</span>
                                                <span class="text-[10px] text-slate-400">{e['created_at'][:16]}</span>
                                            </td>
                                            <td class="p-3">
                                                <span class="font-mono font-bold text-slate-900 block">₹{e['amount']:,.2f}</span>
                                                <span class="text-[10px] text-slate-500">{f"{e['liters']}L @ ₹{e['rate']}/L | Odo: {e['odometer']} KM" if e['exp_type'] == 'FUEL' else f"Odo: {e['odometer']} KM"}</span>
                                            </td>
                                            <td class="p-3">
                                                {f"<span class='text-[10px] font-bold bg-rose-600 text-white px-2 py-0.5 rounded'>{e['flag_reason']}</span>" if e['is_flagged'] else "<span class='text-[10px] font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded'>✅ VERIFIED</span>"}
                                            </td>
                                            <td class="p-3 text-right space-x-1">
                                                {f"""
                                                <a href='/action-expense?id={e['id']}&action=APPROVE' class='text-[10px] bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-2 py-1 rounded transition'>Approve</a>
                                                <a href='/action-expense?id={e['id']}&action=REJECT' class='text-[10px] bg-rose-600 hover:bg-rose-700 text-white font-bold px-2 py-1 rounded transition'>Deduct</a>
                                                """ if e['is_flagged'] and e['manager_status'] == 'PENDING' else f"<span class='text-[10px] font-bold text-slate-500 uppercase'>{e['manager_status']}</span>"}
                                            </td>
                                        </tr>
                                        ''' for e in expenses]) if expenses else '<tr><td colspan="4" class="p-6 text-center text-slate-400">No expenses recorded yet. Use the WhatsApp simulator to log receipts.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                    </div>

                    <!-- Bottom Action Bar: 1-Click Settlement PDF -->
                    <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex justify-between items-center gap-3">
                        <div>
                            <span class="text-[10px] font-bold uppercase text-slate-400 block">Final Settlement Due</span>
                            <span class="text-base font-black text-emerald-700">₹{remaining_advance:,.2f} to recover</span>
                        </div>
                        
                        <div class="flex items-center gap-2">
                            <a href="/generate-settlement-pdf?trip_code={active_trip['trip_code'] if active_trip else ''}" target="_blank" class="bg-sky-600 hover:bg-sky-500 text-white font-bold px-5 py-2.5 rounded-xl text-xs transition shadow flex items-center gap-1.5">
                                📄 Generate 1-Click Settlement PDF
                            </a>
                        </div>
                    </div>

                </div>

            </div>
        </div>

        <!-- Modal: Start New Trip -->
        <div id="newTripModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm hidden flex items-center justify-center p-4 z-50">
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
                        <button type="submit" class="w-full bg-sky-600 hover:bg-sky-700 text-white font-bold py-2.5 rounded-xl transition shadow">
                            🚀 Start Trip & Send WhatsApp Alert
                        </button>
                    </div>
                </form>
            </div>
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
    advance_amount: float = Form(...),
    start_odo: float = Form(...)
):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO trips (trip_code, vehicle_no, driver_name, advance_amount, start_odo, current_odo, status)
                 VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')''',
                 (trip_code, vehicle_no, driver_name, advance_amount, start_odo, start_odo))
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
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                 (trip_code, exp_type, amount, liters, rate, odometer, is_flagged, flag_reason, manager_status))
    
    # Update current vehicle odometer
    if odometer > 0:
        c.execute("UPDATE trips SET current_odo = MAX(current_odo, ?) WHERE trip_code = ?", (odometer, trip_code))
        
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)

@app.get("/action-expense")
def action_expense(id: int, action: str):
    conn = get_db()
    c = conn.cursor()
    status = "APPROVED" if action == "APPROVE" else "REJECTED"
    c.execute("UPDATE expenses SET manager_status = ? WHERE id = ?", (status, id))
    
    # Fetch trip code for redirect
    c.execute("SELECT trip_code FROM expenses WHERE id = ?", (id,))
    row = c.fetchone()
    trip_code = row["trip_code"] if row else ""
    
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/?trip_code={trip_code}", status_code=303)

@app.get("/reset-demo")
def reset_demo():
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM expenses")
    c.execute("DELETE FROM trips")
    init_db()
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

# --- 1-CLICK SETTLEMENT PDF GENERATOR ---
@app.get("/generate-settlement-pdf")
def generate_settlement_pdf(trip_code: str = "TRIP-101"):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM trips WHERE trip_code = ?", (trip_code,))
    trip = c.fetchone()
    c.execute("SELECT * FROM expenses WHERE trip_code = ? ORDER BY id ASC", (trip_code,))
    expenses = c.fetchall()
    conn.close()

    if not trip:
        return Response("Trip not found", status_code=404)

    total_approved = sum([e["amount"] for e in expenses if e["manager_status"] == "APPROVED" or (not e["is_flagged"] and e["manager_status"] != "REJECTED")])
    total_flagged = sum([e["amount"] for e in expenses if e["is_flagged"]])
    net_returnable = trip["advance_amount"] - total_approved

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
            Paragraph("<b>Net Driver Due</b>", cell_style)
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
        details = f"{e['liters']}L @ Rs. {e['rate']}/L (Odo: {e['odometer']} KM)" if e['exp_type'] == 'FUEL' else f"Odo: {e['odometer']} KM"
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
    uvicorn.run(app, host="127.0.0.1", port=8080)