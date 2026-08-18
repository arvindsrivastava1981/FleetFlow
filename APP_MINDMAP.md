# VahanKhata — Master System Mindmap & Agent Reference

> **Purpose:** This file serves as the definitive architecture map, routing table, and protocol guide for AI coding agents (Cline / Roo Code) working within the `VahanKhata` repository. Refer to this document first to avoid exploratory file searches and save context tokens.

## Stack
- Backend: Python 3.12, FastAPI, uvicorn, reportlab (PDF), psycopg2-binary, python-dotenv.
- Database: Managed PostgreSQL (Neon DB). No ORM, no Alembic. Schema lives only in `/database/schema.sql` (+ `/database/incremental.sql`). The app never runs DDL.
- Frontend: Server-rendered HTML strings (f-strings) styled with Tailwind CDN (`grid grid-cols-1 lg:grid-cols-12 gap-4`). No separate JS build.

## Entry Point
- **[backend/app/main.py](/backend/app/main.py)** — the modular FastAPI factory; the **only entry point** (migration complete).
  - Run: `uvicorn backend.app.main:app --app-dir /app --host 0.0.0.0 --port ${PORT:-10000}` (see `Dockerfile` / `render.yaml`, which point here).
  - Wires every router in `backend/app/api/{auth,trips,expenses,demo,dashboard,benchmarks,rule_engine,settlement,views}.py` (see Routes below) + exposes `/healthz` (DB liveness probe).
  - Config/security live in `backend/app/core/{config,security}.py` (env-driven, fail-fast; prod refuses).
  - **Auth hardening (all routers):** every mutation and page guards via `security.require_auth` → 303 to `/login` when unauthenticated; sessions carry a 72h TTL; login has per-IP brute-force lockout (`login_max_attempts=5`, `login_lockout_seconds=300`); state-changing requests use single-use CSRF tokens; all DB-sourced values are escaped via `security.esc()` (stored-XSS fix). Sessions/attempts are process-local in-memory (single-worker); swap `__sessions`/`_login_attempts`/`_csrf_tokens` for a shared store in multi-worker deploys.
- **Legacy `fleetflow_interactive_demo.py` + `utils.py` have been deleted** — every route and helper they contained (rules engine, HTML chrome, DB access,  auth) now lives in the `backend/app/` package (see Routes below and `PROJECT_STRUCTURE.md` §4). Do not reintroduce either file.
- [/start.ps1](/start.ps1) — Windows/PowerShell launcher (validate-then-run, non-mutating until start). Validates Python 3.12+, deps, `.env` (`DATABASE_URL`/`_PASSWORD`), `database/schema.sql`, and the modular entry point against `Installation.md` §§1-6; if all required checks pass, starts the deploy target `uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}` (Installation.md §5). Pass `-CheckOnly` to run validation without launching the server; optional items (`.venv`, `incremental.sql`, legacy-file absence) are reported but do not fail. Pure status snapshot: see `/stat.ps` (`powershell -NoProfile -ExecutionPolicy Bypass -Command ". .\stat.ps"`).
- Legacy SQLite prototypes (`init_db.py`, `fleetflow_backend_core.py`) have been removed; do not reintroduce SQLite.

## Database Access Pattern (Postgres/Neon)
- Connection: `psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=psycopg2.extras.RealDictCursor)`.
- Global `DEC2FLOAT` type caster registered at startup so `NUMERIC` columns arrive as Python `float`, not `Decimal`.
- Placeholders: `%s` only (never `?`).
- `created_at`/timestamps are native `datetime` objects — always format via `fmt_dt(dt)` helper, never slice (`dt[:16]` crashes).
- No `init_db()` / DDL in the app — schema + seed data are applied manually to Neon from `/database/schema.sql`.

### Core Tables (see [/database/schema.sql](/database/schema.sql))
- `subscription_plans` (id, code UNIQUE: TRIAL/MONTHLY/YEARLY, name, billing_cycle, trial_days, price, vehicle_limit, is_active) — product catalogue. TRIAL = 15 days/₹0/1 vehicle; MONTHLY = ₹799/1 vehicle; YEARLY = ₹7,191 (25% off)/1 vehicle.
- `fleets` (id, owner_name, phone UNIQUE, email, subscription_plan, plan_rate, plan_id FK→subscription_plans, subscription_status: TRIAL/ACTIVE/PAST_DUE/CANCELLED/EXPIRED, trial_started_at, trial_ends_at, vehicle_limit, next_billing_date, razorpay_subscription_id, razorpay_customer_id, is_active, created_at/updated_at). Owns the subscription entitlement — trial clock, vehicle cap, and Razorpay billing references.
- `vehicles` (id, fleet_id FK, vehicle_number UNIQUE, make_model, tank_capacity_liters default 350.00, expected_km_per_liter default 4.00, owner_phone, created_by FK→users, is_active). `created_by` scopes vehicles to the Trip Manager / Super Admin who registered them; `fleet_id` binds the vehicle to a fleet and counts against its `vehicle_limit`.
- `trips` (trip_code UNIQUE, vehicle_id FK, vehicle_no, driver_name, driver_phone, advance_amount, start_odo, current_odo, end_odo, status CHECK ACTIVE/COMPLETED/SETTLED/CANCELLED, origin, destination, created_by FK→users, driver_user_id FK→users, created_at, completed_at, settled_at). `created_by` is the manager who started the trip; `driver_user_id` links the assigned driver.
- `expenses` (id, trip_id FK, trip_code FK, exp_type: FUEL/TOLL/REPAIR/CHALLAN/RTO-FINE/DEF/OTHER/MISC/GOODS_BUY/GOODS_SALE, amount, approved_amount, liters, rate, odometer, station_name, is_flagged, flag_reason, manager_status: PENDING/APPROVED/REJECTED, receipt_image_url, raw_receipt_text, created_at/updated_at). Goods buys and sales always start pending; only approved entries affect settlement, with buys reducing and sales increasing cash and trip profit.
- `fuel_benchmarks` (id, state_code, state_name, benchmark_price_per_liter, tolerance_pct default 0.08, effective_date, updated_at) — per-state fuel price index for the anomaly rules engine (managed via the `/fuel-benchmarks`  CRUD).

## Routes
> Migration complete: every route now lives in `backend/app/api/*` (guarded by
> `require_auth` — unauthenticated → 303 `/login` — except the public `/login`
> page and `/healthz`). There is no separate prototype surface anymore.

### `backend/app/api/*` (security-hardened, all -guarded unless noted)
- `GET /login`, `POST /login`, `GET /logout` — `api/auth.py`: TTL sessions via `create_session`, per-IP brute-force lockout, secure cookie (httponly, samesite=lax). Wrong password → `303 /login?error=1`. `GET /login` is public.
- `POST /create-trip` — `api/trips.py`: inserts `trips` row (validates plate regex, `+91` phone, non-negative advance/odo; blocked if another ACTIVE trip exists). Captures `created_by` (logged-in manager), `driver_user_id` + `vehicle_id` from the Start-Trip modal dropdowns.
- `GET /settle-trip?trip_code=` — `api/trips.py`: marks trip `SETTLED` (only when no PENDING expenses remain).
- `POST /simulate-whatsapp` — `api/expenses.py`: runs `evaluate_expense()` then inserts an `expenses` row (goods stay pending; flagged → pending); upserts `trips.current_odo`.
- `GET /action-expense?id=&action=APPROVE|REJECT` — `api/expenses.py`: manager decision on a flagged/pending expense or goods transaction.
- `GET /fleets` + `GET /fleets/create`, `POST /fleets/create`, `GET /fleets/edit/{id}`, `POST /fleets/edit/{id}`, `GET /fleets/deactivate/{id}`, `GET /fleets/activate/{id}` — `api/fleets.py`: **Fleet CRUD** (Super Admin only). Creates a fleet that starts a 15-day trial with 1 vehicle. Shows subscription status, plan, and vehicle count.
- `GET /billing/upgrade` + `POST /billing/subscribe` — `api/billing.py`: choose monthly (₹799) or yearly (₹7,191, 25% off) plan, initiate Razorpay subscription checkout.
- `GET /billing/vehicle-slot` + `POST /billing/vehicle-slot` — `api/billing.py`: purchase additional vehicle slot when fleet hits its cap (upsell page + Razorpay payment link).
- `POST /billing/webhook` — `api/billing.py`: Razorpay server→server callback (HMAC-SHA256 signature verified). Handles `subscription.activated/charged/cancelled/failed` and `payment_link.paid`.
- `GET /reset-demo` — `api/demo.py`: clears `expenses`+`trips` rows (no DDL, no reseed).
- `GET /dashboard` — `api/dashboard.py`: -only savings dashboard (money-saved/claimed/approved/**pending** cards + per-trip Chart.js bar chart); fallback landing page. **Role-scoped**: trip_manager sees only their own trips' figures, driver only their assigned trips, super_admin sees all.
- `GET /admin` — `api/dashboards.py`: **Super Admin** macro dashboard (role-gated via `require_role(..., "super_admin")`): Active Fleet, Fuel & Road Spend (MTD), Leakage Prevented (REJECTED sum), Outstanding Cash Float; anomaly heatmap, km/L-efficiency leaderboard vs. `vehicles.expected_km_per_liter`, settlement approval summary + quick actions. Query helpers in `db/queries/dashboards.py`.
- `GET /manager` — `api/dashboards.py`: **Trip Manager** dashboard (`require_role("trip_manager","super_admin")`): dispatched trips, pending escalations, advances disbursed today, awaiting-settlement count; live escalation feed with 1-click Approve/Deduct (`/action-expense`), active-trip progress table, 1-click settlement queue. **All figures scoped to trips the logged-in manager created** (`manager_kpis`/`open_escalations`/`active_trip_progress`/`settlement_ready_trips` filter by `created_by`); super_admin sees everything.
- `GET /driver` — `api/dashboards.py`: **Driver** dashboard (`require_role("driver")`): live status card (active trip, advance, cash-in-hand = advance + approved net, logged-today), quick-log actions, recent expense logs + trip-end summary.
- `POST /login` now redirects by role: `super_admin → /admin`, `trip_manager → /manager`, `driver → /driver` (fallback `/dashboard`).
- `GET /` — `api/views.py`: 3-column dual-WhatsApp workspace UI (see UI Layout below); **scoped** so a manager/driver can only open their own trips. The Start New Trip modal loads **Vehicle Number + Driver dropdowns** populated from the manager's registered vehicles (by `created_by`) and the active driver accounts.
- `GET /vehicles` + `GET /vehicles/create`, `POST /vehicles/create`, `GET /vehicles/edit/{id}`, `POST /vehicles/edit/{id}`, `GET /vehicles/deactivate/{id}`, `GET /vehicles/activate/{id}` — `api/vehicles.py`: **Vehicle CRUD** (role-gated to `trip_manager`/`super_admin`). Managers see/register only the vehicles they created (`created_by`), and these feed the Vehicle Number dropdown in the Start-Trip modal. Plates validated against the regex.
- `GET /trips` — `api/views.py`: trip listing (active first) with per-trip expense totals / pending counts; **scoped by role** — a trip_manager only sees trips they created (`created_by`), a driver only their assigned trips, super_admin sees all. "Start New Trip" disabled while a trip is active.
- `GET /` — `api/views.py`: tabular all-trips overview (legacy  landing page).
- `GET /fuel-benchmarks` + `POST /fuel-benchmarks/add`, `POST /fuel-benchmarks/edit`, `GET /fuel-benchmarks/delete?id=` — `api/benchmarks.py`:  CRUD for per-state fuel price benchmarks.
- `GET /rule-engine` — `api/rule_engine.py`: read-only explainer of the anomaly rules per expense type (static `settings` constants only, no DB).
- `GET /settled-pdfs` — `api/settlement.py`: lists settled trips with links to their settlement PDFs (scoped to the caller's own trips).
- `GET /generate-settlement-pdf?trip_code=` — `api/settlement.py`: builds a reportlab PDF settlement/reconciliation sheet via `services/pdf/settlement.py`.

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
- Rules engine constants: `BENCHMARK_PRICE=90.50`, `TANK_CAPACITY=350.0L`, `EXPECTED_KML=4.0`, `DEF_RATE_MAX=75.0`, `DEF_MIN_RATIO_PCT=3.0`, `DEF_MAX_RATIO_PCT=6.0`. (Note: `fuel_benchmarks` table exists with per-state prices, but `evaluate_rules()` currently uses the global `BENCHMARK_PRICE` constant — per-state lookup is not yet wired in.)

---

## Future Enhancements (product spec gaps — see docs/implementation_plan.md)

> Source of truth for the roadmap: `docs/implementation_plan.md`. These are **not yet implemented**; do not assume they exist. Plan the work as: **Phase A → B → C → D → E → F**.

- **G1 — Real WhatsApp Cloud API** (`POST /whatsapp/webhook`): inbound media + outbound message templates + session binding by WhatsApp number. Today only the browser simulator (`/simulate-whatsapp`) exists. Needs `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_ID`, `WEBHOOK_VERIFY_TOKEN` env vars.
- **G2 — AI OCR / Vision receipt parsing**: extract Amount, Liters, Rate, Pump Name, Odometer from fuel receipts + odometer photos. No OCR library/model wired; `raw_receipt_text`/`receipt_image_url` columns exist but are never populated.
- **G3 — Dual-photo evidence protocol + EXIF check** for REPAIR (damaged-part photo + mechanic invoice, EXIF metadata validation). Currently UI-hint text only.
- **G4 — State-dynamic fuel benchmark**: drive the ±8% band from `fuel_benchmarks` per trip/state instead of the global `BENCHMARK_PRICE`.
- **G5 — FASTag corridor whitelisting**: differentiate legit cash toll on off-corridor roads vs. flagged cash toll on 100% FASTag corridors. Requires a new `toll_corridors` table + `corridor` field on expenses.
- **G6 — Photo/WhatsApp-based trip initiation & driver onboarding** (bind driver WhatsApp number, bot greeting).
- **G7 — Sub-3s log parsing with no manual driver text input**.
- **G8 — Bilingual (Hindi/English) + audio confirmations** to driver.
- **G9 — Live WhatsApp bot verification replies** to driver.
- **G10 — Mandatory dashboard-odometer photo at fuel entry** (server-enforced, not just hint).
- **G11 — Anti-fraud EXIF/metadata tamper check + verified parts** for repairs.
- **G12 — Explicit manager confirmation for any deduction** (labor-protection) — mostly satisfied by existing `/action-expense`; extend confirmation message language.
- **G13 — Product-doc artifacts** (ROI/unit-economics tables, competitive matrix, DPDPA privacy statement) — optional additions to `README.md`; no code needed.

### Implementation phases (from docs/implementation_plan.md)
- **Phase A — Rules/data-model upgrades:** benchmark-aware `evaluate_rules()`, corridor toll rule, dual-photo/odometer enforcement, EXIF check (no external creds).
- **Phase B — DB schema:** add `toll_corridors`, new `expenses` columns (`corridor`, `evidence_photos`, `exif_ok`); update `schema.sql` + `incremental.sql`, seed `toll_corridors`.
- **Phase C — WhatsApp Cloud API:** webhook route, media receive, outbound templates, inbound trip init.
- **Phase D — OCR pipeline:** OCR dep + post-processing, persist `raw_receipt_text`, odometer cross-check.
- **Phase E — UX:** bilingual/audio confirmations, driver verification slip.
- **Phase F — Tests & docs:** unit tests for new rules/OCR; update `README.md`, `docs/product_details.md`, and this file.

