import sqlite3

def create_and_seed_db():
    conn = sqlite3.connect("fleetflow_demo.db")
    c = conn.cursor()
    
    # 1. Trips table
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
    
    # 2. Expenses table
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
    
    # Reset & Seed
    c.execute("DELETE FROM trips")
    c.execute("DELETE FROM expenses")
    
    c.execute("INSERT INTO trips (trip_code, vehicle_no, driver_name, advance_amount, start_odo, current_odo) VALUES ('TRIP-901', 'UP-93-AT-1234', 'Ramesh Kumar', 25000, 102400, 103200)")
    
    # Pre-seeded test cases (1 verified fuel, 1 flagged toll, 1 flagged mileage skim, 1 verified repair)
    c.execute("INSERT INTO expenses (trip_code, exp_type, amount, liters, rate, odometer, is_flagged, flag_reason) VALUES ('TRIP-901', 'FUEL', 4500, 50, 90.0, 102600, 0, '')")
    c.execute("INSERT INTO expenses (trip_code, exp_type, amount, liters, rate, odometer, is_flagged, flag_reason) VALUES ('TRIP-901', 'TOLL', 850, 0, 0, 102750, 1, 'Cash claimed on FASTag corridor')")
    c.execute("INSERT INTO expenses (trip_code, exp_type, amount, liters, rate, odometer, is_flagged, flag_reason) VALUES ('TRIP-901', 'FUEL', 5400, 60, 90.0, 102850, 1, 'Low mileage 1.7 km/L (Expected 4.0)')")
    c.execute("INSERT INTO expenses (trip_code, exp_type, amount, liters, rate, odometer, is_flagged, flag_reason) VALUES ('TRIP-901', 'REPAIR', 350, 0, 0, 103200, 0, '')")
    
    conn.commit()
    conn.close()
    print("fleetflow_demo.db successfully created and seeded with test cases.")

if __name__ == "__main__":
    create_and_seed_db()
