# FleetFlow — Master System Mindmap & Agent Reference

> **Purpose:** This file serves as the definitive architecture map, routing table, and protocol guide for AI coding agents (Cline / Roo Code) working within the `FleetFlow` repository. Refer to this document first to avoid exploratory file searches and save context tokens.

## Stack
- Backend: Python 3.12, FastAPI, uvicorn, reportlab (PDF), psycopg2-binary, python-dotenv.
- Database: Managed PostgreSQL (Neon DB). No ORM, no Alembic. Schema lives only in `demo/database/schema.sql` (+ `demo/database/incremental.sql`). The app never runs DDL.
- Frontend: Server-rendered HTML strings (f-strings) styled with Tailwind CDN (`grid grid-cols-1 lg:grid-cols-12 gap-4`). No separate JS build.

## Entry Point
- [demo/fleetflow_interactive_demo.py](demo/fleetflow_interactive_demo.py) — single-file FastAPI demo app, the active/primary prototype.
  - Run: `uvicorn fleetflow_interactive_demo:app` or `python fleetflow_interactive_demo.py` (binds `0.0.0.0:$PORT`, default 8080).
  - Deps: [demo/requirements.txt](demo/requirements.txt).
- Legacy SQLite prototypes (`init_db.py`, `fleetflow_backend_core.py`) have been removed; do not reintroduce SQLite.

## Database Access Pattern (Postgres/Neon)
- Connection: `psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=psycopg2.extras.RealDictCursor)`.
- Global `DEC2FLOAT` type caster registered at startup so `NUMERIC` columns arrive as Python `float`, not `Decimal`.
- Placeholders: `%s` only (never `?`).
- `created_at`/timestamps are native `datetime` objects — always format via `fmt_dt(dt)` helper, never slice (`dt[:16]` crashes).
- No `init_db()` / DDL in the app — schema + seed data are applied manually to Neon from `demo/database/schema.sql`.

### Core Tables (see [demo/database/schema.sql](demo/database/schema.sql))
- `trips` (trip_code, vehicle_no, driver_name, driver_phone, advance_amount, start_odo, current_odo, status, created_at, settled_at).
- `expenses` (trip_code FK, exp_type: FUEL/TOLL/REPAIR/..., amount, liters, rate, odometer, is_flagged, flag_reason, manager_status: PENDING/APPROVED/REJECTED, created_at).

## Routes (fleetflow_interactive_demo.py)
- `GET /` — renders the 3-column dashboard (see UI Layout below).
- `POST /create-trip` — inserts a new `trips` row (requires driver_phone), redirects to `/?trip_code=...`.
- `POST /simulate-whatsapp` — inserts an `expenses` row after running it through `evaluate_rules()` (fuel math/price-band/tank-capacity/odometer-mileage checks, mandatory TOLL flag, REPAIR > ₹3,000 flag).
- `GET /action-expense?id=&action=APPROVE|REJECT` — manager decision on a flagged expense.
- `GET /reset-demo` — clears `expenses`/`trips` rows only (no reseed, no DDL).
- `GET /generate-settlement-pdf?trip_code=` — builds a reportlab PDF settlement/reconciliation sheet.

## UI Layout — 3-Column Dual-WhatsApp Architecture (`GET /`)
`grid grid-cols-1 lg:grid-cols-12 gap-4`, 3 equal `lg:col-span-4` columns:
1. **Driver WhatsApp** — chat-style simulator where the driver "sends" expense receipts (form posts to `/simulate-whatsapp`).
2. **Manager WhatsApp Escalation** — chat thread showing only flagged expenses with inline Approve/Deduct quick-reply links (posts to `/action-expense`).
3. **Master Ledger** — trip summary card, financial metrics (Claimed/Approved/Flagged/Cash in Hand), read-only ledger table, and the 1-click Settlement PDF action.

## System Invariants
- Vehicle Plate Regex: `^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$`
- Country Code: `+91`
- QR Code Length: 6 characters
- Normalized Alert Issue: `issue_type="Emergency"`
- Anti-Spam: 3 scans / hour per tag
- OTP Constraints: 6-digit code, 10-minute expiry, 3 verification attempts, 60-second request cooldown
- JWT Session: 72 hours
- Contact Form Cooldown: 60 seconds per source IP
- Rules engine constants: `BENCHMARK_PRICE=90.50`, `TANK_CAPACITY=350.0L`, `EXPECTED_KML=4.0`.

