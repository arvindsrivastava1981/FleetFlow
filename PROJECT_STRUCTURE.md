# FleetFlow — Production Folder Structure & Module Map

> **Purpose:** Defines the target, best-in-class folder structure for FleetFlow.
> It decomposes the current single-file prototype (`fleetflow_interactive_demo.py`
> + `utils.py`) into a layered FastAPI package, resolves every
> `docs/deep_agent_recommendation.md` issue in the module design, and gives each
> future phase (`docs/implementation_plan.md`, `docs/product_details.md`) a
> permanent home.
>
> **Deploy status:** The container/deploy entrypoint is already switched to the
> new package (`backend.app.main:app` in `Dockerfile`; `render.yaml` now declares
> the required secrets + a `/healthz` health check). See §4 for the cutover note.

---

## 1. Target Tree (created in this pass)

```
FleetFlow/
├── backend/                          # Python application package
│   ├── __init__.py
│   └── app/
│       ├── __init__.py
│       ├── main.py                   # FastAPI factory; /healthz + root probe
│       ├── api/                      # router manifest (route owners)
│       │   ├── dashboard.py          # GET /dashboard
│       │   ├── trips.py              # GET /trips, POST /create-trip, /settle-trip
│       │   ├── expenses.py           # POST /simulate-whatsapp, GET /action-expense
│       │   ├── settlement.py         # /settled-pdfs, /generate-settlement-pdf
│       │   ├── benchmarks.py         # fuel-benchmarks page + CRUD
│       │   ├── rules.py              # GET /rule-engine
│       │   ├── auth.py               # GET/POST /login, GET /logout
│       │   ├── demo.py               # GET /reset-demo (admin-only)
│       │   ├── health.py             # GET /healthz
│       │   ├── whatsapp/webhook.py   # POST /whatsapp/webhook  (Phase C)
│       │   └── ocr/callback.py       # POST /ocr/callback       (Phase D)
│       ├── core/                     # config + security (no DB)
│       │   ├── config.py             # env-driven, fail-fast settings
│       │   ├── security.py           # auth, sessions, CSRF, login-lock, esc()
│       │   └── logging.py            # structured logging (todo)
│       ├── db/                       # persistence (no HTTP)
│       │   ├── connection.py         # get_db() contextmanager + DEC2FLOAT
│       │   └── queries/              # trips.py, expenses.py, fuel_benchmarks.py
│       ├── models/                   # typed domain access (Fleet, Vehicle, Trip,
│       │   │                         #   Expense, FuelBenchmark, TollCorridor)
│       ├── schemas/                  # Pydantic v2 in/out contracts + enums
│       ├── services/                 # pure business logic, no Request/HTML
│       │   ├── rules/                # ANOMALY ENGINE (pure, testable)
│       │   │   ├── constants.py      # thresholds (single source of truth)
│       │   │   ├── bands.py          # benchmark-derived fuel band
│       │   │   ├── evaluate.py       # evaluate_expense() -> RuleVerdict
│       │   │   ├── toll.py           # corridor-aware TOLL rule (Phase A/B)
│       │   │   └── evidence.py       # dual-photo + EXIF enforcement (Phase A/B)
│       │   ├── audit/                # settlement math + savings derivation
│       │   ├── pdf/                  # reportlab settlement sheets
│       │   ├── whatsapp/             # Meta Cloud API client + webhook (Phase C)
│       │   ├── ocr/                  # receipt/odometer vision parsing (Phase D)
│       │   └── notify/               # bilingual + audio confirmations (Phase E)
│       └── web/                      # server-rendered presentation
│           ├── chrome.py             # render_header/footer/sidebar
│           ├── dashboard.py / trips.py / expenses.py / settlement.py
│           ├── benchmarks.py / rules.py
│           ├── templates/            # Tailwind-CDN page shells (future)
│           └── static/               # reusable JS fragments (future)
├── database/                         # schema + seed (manual DDL only)
│   ├── schema.sql                    # master DDL
│   ├── incremental.sql               # changelog statements
│   ├── seed.sql                      # demo seed
│   ├── cleanup.sql
│   ├── migrations/                   # named migration files
│   └── seed/                         # production-reference seed
├── tests/
│   ├── conftest.py                   # repo-root on path + shared fixtures
│   ├── unit/rules/
│   │   └── test_evaluate.py          # 15 passing rules-engine tests
│   ├── integration/                  # DB-backed route tests (future)
│   └── fixtures/                     # throwaway sample data + expected verdicts
├── scripts/
│   ├── run_tests.py                  # `python scripts/run_tests.py`
│   └── smoke_check.py                # env + band + import-path sanity
├── docs/                             # product + plan + review docs
├── pyproject.toml                    # pytest/black/ruff config
├── requirements.txt, Dockerfile, render.yaml
└── (legacy, until migration completes)
    ├── fleetflow_interactive_demo.py
    └── utils.py
```
---

## 2. How It Fixes `docs/deep_agent_recommendation.md`

| # | Severity | Issue | Where the structure solves it |
|---|---------|-------|------------------------------|
| 2.1 | CRIT | Unauthenticated mutation endpoints | `api/*` routers use `core.security.require_admin()` / `admin_auth` on **every** mutation; `demo.py` isolates `/reset-demo` |
| 2.2 | CRIT | Weak/hardcoded password, no login hardening | `core/config.py` (fail-fast, prod refuses `admin123`), `core/security.py` (rate-limit + lockout) |
| 2.3 | HIGH | Stored XSS via f-strings | `core/security.esc()` used by every `web/*` page builder; scoped HTML lives only in `web/` |
| 2.4 | MED | No CSRF | `middleware/csrf.py` + `core/security.validate_csrf_token()` for all POSTs |
| 2.5 | HIGH | Hardcoded 82/98 fuel band | `services/rules/bands.py` derives `90.50 +/- 8%` (83.26-97.74), proven by tests |
| 2.6 | MED | Flagged/approved double-count | `services/audit/` centralises "flagged = REJECTED only" once |
| 2.7 | MED | `expenses.trip_id` never set | `models/expenses` resolves `trip_id` at insert (or a migration drops it) |
| 2.8 | MED | Mileage ignores non-FUEL odo | `services/rules/evaluate.py` takes `prev_odo` from latest expense of any type |
| 2.9 | MED | Settlement sign conventions | `services/audit/cash.py` named helpers + focused tests |
| 3.1 | HIGH | No test suite | `tests/` + `pyproject.toml`; `tests/unit/rules/test_evaluate.py` (15 tests) |
| 3.4 | MED | No structured connection cleanup | `db/connection.py` `contextmanager` |
| 3.5 | MED | No input validation | `schemas/*` Pydantic models + System Invariants enums |
| 3.6 | MED | No health check / error handling | `main.py` `/healthz` + `health.py` router |

---

## 3. Where Future Phases Land

| Phase / Gap | Home |
|-------------|------|
| A1 benchmark rules (G4) | `services/rules/bands.py` + `db/queries/fuel_benchmarks.py` |
| A2 corridor toll (G5) | `services/rules/toll.py`, `models/TollCorridor`, `database/seed` |
| A3 dual-photo / odometer (G10) | `services/rules/evidence.py`, `schemas/expenses`, `db/queries` |
| A4 EXIF check (G3) | `services/rules/evidence.py` |
| B schema | `database/migrations/` |
| C WhatsApp (G1/G6/G9) | `services/whatsapp/` + `api/whatsapp/webhook.py` |
| D OCR (G2/G7) | `services/ocr/` + `api/ocr/callback.py` |
| E bilingual/audio (G8) | `services/notify/` |
| F tests/docs | `tests/`, `docs/`, `APP_MINDMAP.md` |

---
## 4. Migration Path (incremental, non-breaking)

The prototype still runs today for local dev. The new package is additive — no
existing Python source file is touched during this restructure, and the **deploy
artifacts already point at the new entrypoint**:

- `Dockerfile` CMD now runs `uvicorn backend.app.main:app --app-dir /app ...`
- `render.yaml` adds a `/healthz` web-health-check and declares the required
  secrets (`DATABASE_URL`, `ADMIN_PASSWORD`, `ENV=production`).

Migrate feature-by-feature:

1. **Rules engine** — done. `services/rules/*` hosts `evaluate_rules()` plus the
   pure `evaluate_expense()`. The legacy import path still works via the
   compatibility shim in `evaluate.py`.
2. **Config/security** — done for `core/config.py` + `core/security.py`; these are
   the single sources. Wire `utils.py` to delegate as routes migrate.
3. **DB layer** — `db/connection.py` becomes the only place that opens a connection.
4. **Transport (routers)** — copy each handler into the matching `api/*.py`, swapping
   `conn.cursor()` for `get_db()` and adding `esc()` + `require_admin()`. Delete each
   prototype block once no route references it.

> **Note on rollback during the cutover:** if you deploy with `backend.app.main` and the
> router migration isn't complete, the container serves only `/healthz` and `/` — it will
> boot healthy but not yet expose the ledger/trips UI. Until all routers are ported,
> keep the old prototype available for local demo (`uvicorn fleetflow_interactive_demo:app`),
> or run the app factory once routers land. The production UI should only be switched to the
> packaged factory after step 4 finishes.
>
> **Once every router is migrated:** delete `utils.py` + `fleetflow_interactive_demo.py`
> and the deploy entrypoint is already correct — no further change needed.

---

## 5. Convention Invariants

- **No SQL in routers.** Queries live in `db/queries/`, wrapped by `models/`.
- **No HTML in services.** Presentation lives exclusively in `web/`.
- **No FastAPI/`Request` in services.** Pure funcs take/return plain data.
- **Zero DDL in the app.** Schema changes go to `database/` only.
- **Every dynamic DB value passes `esc()`** before HTML interpolation.
- **Every mutation route guards with `require_admin()`/`admin_auth`.**
- **Pure rules depend only on `core/config` value objects** (no direct DB coupling),
  so unit tests run without a live database.