import sqlite3
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from weasyprint import HTML

app = FastAPI(title="FleetFlow Engine")
DB_FILE = "fleetflow_demo.db"

# --- ANOMALY DETECTION ENGINE ---
def evaluate_expense(exp_type: str, amount: float, liters: float, rate: float, odo: float, trip_code: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
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
            # Check mileage delta from previous fuel fill
            c.execute("SELECT odometer FROM expenses WHERE trip_code = ? AND exp_type = 'FUEL' AND odometer > 0 ORDER BY id DESC LIMIT 1", (trip_code,))
            last_fuel = c.fetchone()
            if last_fuel and odo > last_fuel["odometer"] and liters > 0:
                kml = (odo - last_fuel["odometer"]) / liters
                if kml < 2.8: # Expected ~4.0 km/L
                    is_flagged = 1
                    flag_reason = f"Low mileage {kml:.1f} km/L (Expected 4.0)"
    elif exp_type == "TOLL":
        is_flagged = 1
        flag_reason = "Cash claimed on FASTag corridor"

    conn.close()
    return is_flagged, flag_reason
