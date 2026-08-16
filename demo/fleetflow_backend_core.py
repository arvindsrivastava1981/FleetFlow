import sqlite3
from typing import Tuple

DB_FILE = "fleetflow_demo.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_core_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Vehicles Configuration Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_number TEXT UNIQUE,
        tank_capacity_liters REAL DEFAULT 350.0,
        expected_km_per_liter REAL DEFAULT 4.0,
        owner_phone TEXT
    )''')
    
    # Seed default vehicle if not present
    cursor.execute("SELECT count(*) as count FROM vehicles WHERE vehicle_number = 'UP-93-AT-1234'")
    if cursor.fetchone()["count"] == 0:
        cursor.execute("INSERT INTO vehicles (vehicle_number, tank_capacity_liters, expected_km_per_liter) VALUES ('UP-93-AT-1234', 350.0, 4.0)")
        
    conn.commit()
    conn.close()

init_core_db()

# --- ANOMALY DETECTION CONSTANTS ---
BENCHMARK_DIESEL_PRICE = 90.50  # Dynamic state benchmark baseline
PRICE_TOLERANCE_PCT = 0.08      # 8% tolerance band (₹83.26 - ₹97.74)

def verify_fuel_expense(vehicle_number: str, trip_code: str, liters: float, rate_per_liter: float, amount: float, current_odometer: float) -> Tuple[bool, str]:
    """
    Multi-layer validation rules engine for diesel expenses:
    1. Checks for tank capacity overflows.
    2. Compares unit price against state fuel benchmarks.
    3. Calculates real-time km/L delta against previous odometer photo logs.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Fetch vehicle configuration
    cursor.execute("SELECT * FROM vehicles WHERE vehicle_number = ?", (vehicle_number,))
    veh = cursor.fetchone()
    tank_cap = veh["tank_capacity_liters"] if veh else 350.0
    expected_kml = veh["expected_km_per_liter"] if veh else 4.0
    
    # 2. Fetch last logged odometer reading for this trip
    cursor.execute("SELECT start_odo FROM trips WHERE trip_code = ?", (trip_code,))
    trip = cursor.fetchone()
    start_odo = trip["start_odo"] if trip else 0.0
    
    cursor.execute("SELECT odometer FROM expenses WHERE trip_code = ? AND exp_type = 'FUEL' AND odometer > 0 ORDER BY id DESC LIMIT 1", (trip_code,))
    last_exp = cursor.fetchone()
    prev_odo = last_exp["odometer"] if last_exp and last_exp["odometer"] else start_odo
    
    flags = []
    
    # Rule A: Tank Capacity Overflow
    if liters > tank_cap:
        flags.append(f"Fuel quantity ({liters}L) exceeds tank capacity ({tank_cap}L)")
        
    # Rule B: Fuel Rate Benchmark Discrepancy
    min_rate = BENCHMARK_DIESEL_PRICE * (1 - PRICE_TOLERANCE_PCT)
    max_rate = BENCHMARK_DIESEL_PRICE * (1 + PRICE_TOLERANCE_PCT)
    if rate_per_liter > max_rate or (rate_per_liter > 0 and rate_per_liter < min_rate):
        flags.append(f"Rate ₹{rate_per_liter}/L outside benchmark band (₹{min_rate:.1f}-₹{max_rate:.1f}/L)")
        
    # Rule C: Mileage Skimming (km/L delta drop > 30%)
    if current_odometer and prev_odo and current_odometer > prev_odo and liters > 0:
        km_run = current_odometer - prev_odo
        calc_kml = km_run / liters
        if calc_kml < (expected_kml * 0.70):  # Flags anything below 2.8 km/L for a 4.0 km/L expected vehicle
            flags.append(f"Low mileage {calc_kml:.2f} km/L detected (Expected ~{expected_kml:.1f} km/L)")
            
    conn.close()
    return (len(flags) > 0, "; ".join(flags))

def verify_toll_expense(route_is_fastag_corridor: bool = True, is_cash_claim: bool = True) -> Tuple[bool, str]:
    """Flags cash toll reimbursement claims on routes identified as FASTag-mandated."""
    if route_is_fastag_corridor and is_cash_claim:
        return True, "Cash claimed on FASTag corridor"
    return False, ""
