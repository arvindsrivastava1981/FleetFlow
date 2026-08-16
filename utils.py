import os
import secrets
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import Request

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# PostgreSQL NUMERIC columns arrive as Decimal; cast to float globally to avoid arithmetic TypeErrors
DEC2FLOAT = psycopg2.extensions.new_type(
    psycopg2.extensions.DECIMAL.values, 'DEC2FLOAT', lambda v, c: float(v) if v is not None else None
)
psycopg2.extensions.register_type(DEC2FLOAT)

# --- DATABASE CONNECTION (schema/tables managed manually via database/schema.sql in Neon) ---
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def fmt_dt(dt) -> str:
    # PostgreSQL returns native datetime objects; never slice a datetime directly
    return dt.strftime('%d %b %H:%M') if hasattr(dt, 'strftime') else str(dt)[:16]

# --- ADMIN AUTH (in-memory session tokens; single-process demo, no new deps) ---
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_COOKIE = "ff_admin_session"
_admin_sessions: set[str] = set()

def is_admin(request: Request) -> bool:
    token = request.cookies.get(ADMIN_COOKIE)
    return bool(token) and token in _admin_sessions

def render_header(authenticated: bool = False) -> str:
    nav_links = (
        '''<a href="/dashboard" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-3 py-2 rounded-xl transition">📊 Dashboard</a>
            <a href="/trips" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-3 py-2 rounded-xl transition">🧾 Trips</a>'''
        if authenticated else ''
    )
    auth_controls = (
        f'''<span class="text-xs text-slate-300 font-semibold">Welcome Admin</span>
            <a href="/logout" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-3 py-2 rounded-xl transition">🚪 Logout</a>'''
        if authenticated else
        '''<a href="/login" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold px-3 py-2 rounded-xl transition">Login</a>'''
    )
    return f'''
        <header class="bg-slate-900 text-white p-5 rounded-2xl flex flex-wrap justify-between items-center shadow-lg gap-4">
            <div class="flex items-center space-x-3">
                <div class="bg-sky-500 p-2 rounded-xl text-white font-black text-xl">FF</div>
                <div>
                    <h1 class="text-xl font-extrabold tracking-tight">FleetFlow</h1>
                    <p class="text-xs text-sky-400 font-medium">Real-Time Expense Verification & Settlement Engine</p>
                </div>
            </div>
            <nav class="flex items-center gap-3">{nav_links}{auth_controls}</nav>
        </header>'''

def render_footer() -> str:
    return '''
        <footer class="text-center text-xs text-slate-400 py-2">
            FleetFlow · Expense verification and settlement
        </footer>'''

def render_sidebar(active: str) -> str:
    def nav_link(href: str, label: str, icon: str, key: str) -> str:
        classes = "bg-sky-600 text-white" if active == key else "text-slate-300 hover:bg-slate-800 hover:text-white"
        return f'<a href="{href}" class="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition {classes}">{icon} {label}</a>'
    return f'''
        <aside class="bg-slate-900 rounded-2xl p-3 w-full lg:w-52 flex-shrink-0 space-y-1 h-fit">
            {nav_link("/dashboard", "Dashboard", "📊", "dashboard")}
            {nav_link("/trips", "Trips", "🧾", "trips")}
            {nav_link("/logout", "Logout", "🚪", "logout")}
        </aside>'''

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
            c.execute("SELECT odometer FROM expenses WHERE trip_code = %s AND exp_type = 'FUEL' AND odometer > 0 ORDER BY id DESC LIMIT 1", (trip_code,))
            last_fuel = c.fetchone()

            if last_fuel:
                prev_odo = last_fuel["odometer"]
            else:
                c.execute("SELECT start_odo FROM trips WHERE trip_code = %s", (trip_code,))
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
