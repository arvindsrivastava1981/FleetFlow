# VahanKhata — Bugs, Issues, Enhancements & Feature Roadmap

> **Generated:** 2026-08 · **Method:** Full-stack audit (auth/session flow, webhook handlers,
> DB access layer, billing idempotency, trip lifecycle, SPA routing/state) after the 2026-08
> dead-code cleanup. Every bug cites file + line evidence.
> Severity: 🔴 Critical · 🟠 High · 🟡 Medium · ⚪ Low.
> **Status legend:** ~~struck~~ ✅ = resolved (see cell for date/notes).

---

## 1. Bugs & Verified Defects

| ID | Sev | Area | Finding | Evidence | Fix sketch |
|----|-----|------|---------|----------|------------|
| B-1 | 🟠 | Auth | ~~Deactivated/password-changed users keep access up to 72 h~~ **FIXED** | `core/security.py`, `api/v1/auth.py`, `api/v1/users.py` | ✅ 2026-08: new `revoke_user_sessions()` — called on change-password and on user/driver deactivation toggles; live tokens die instantly. Fleet-wide since R-1 (revocations also purge the durable store). SPA signs out locally after a password change. |
| B-2 | 🟠 | WhatsApp | ~~Inbound webhook accepts unsigned payloads~~ **FIXED** | `api/v1/whatsapp.py::_signature_valid` + POST handler | ✅ 2026-08: `X-Hub-Signature-256` HMAC verified before parsing/routing (401 on mismatch). Active whenever env `WHATSAPP_APP_SECRET` is set. ⚠️ **Deploy action: add `WHATSAPP_APP_SECRET` to Render env.** |
| B-3 | 🟠 | WhatsApp | ~~`POST /api/v1/whatsapp/send` is unauthenticated~~ **FIXED** | `api/v1/whatsapp.py::whatsapp_send` | ✅ 2026-08: gated via `require_json_role("trip_manager","super_admin")`. Now also live-sends via Graph API (F-1). |
| B-4 | 🟡 | Trips | ~~Trip-code race~~ **FIXED** | `db/queries/trips.py::insert_trip` | ✅ 2026-08: `pg_advisory_xact_lock(hashtext(vehicle_no))` taken before code generation — auto-releases on commit/rollback, serializes across instances, no retry loop needed. |
| B-5 | 🟡 | Ops | ~~`/healthz` leaks raw DB error text~~ **FIXED** | `db/connection.py::healthcheck` | ✅ 2026-08: returns generic `{"db":"error"}`; detail only via `logging.exception`. |
| B-6 | 🟡 | Auth | ~~Session cookie lacks `secure` flag~~ **FIXED** | `api/v1/auth.py` set_cookie | ✅ 2026-08: `secure=settings.cookie_secure` (env `COOKIE_SECURE`, default ON; localhost exempt). |
| B-7 | ⚪ | Auth | ~~Cookie transport redundant~~ **DONE** | `config.py`, `api/v1/auth.py`, `core/security.py` | ✅ 2026-08: cookie issuance now opt-in via env `AUTH_COOKIE=1` (default off — SPA is Bearer-only). Bonus fix: `destroy_session` revokes the **Bearer** token too — logout previously left server-side sessions alive until TTL. |
| B-8 | ⚪ | Billing | ~~Webhook dedupe bypassed when `event_id` empty~~ **FIXED** | `api/webhook.py` | ✅ 2026-08: missing ids fall back to a `sha256:<body>` content hash so dedupe always applies; guard simplified. |
| B-9 | ⚪ | Escalations | ~~Escalation callback URL built from request scheme/netloc~~ **FIXED** | `api/v1/expenses.py` (driver notification) | ✅ 2026-08: uses `settings.app_public_url` when set. Superseded in F-1: notification is now a direct service call (no HTTP hop at all). |
| B-10 | ⚪ | Repo hygiene | ~~Stray `settlement_debug.log`~~ removed; sample PDF still git-tracked (README links it). | root listing; README:31 | ✅ Partial 2026-08: log deleted. To untrack the PDF yourself: `git rm --cached FleetFlow_Sample_Settlement_Sheet.pdf` (no code references it). |
| B-11 | 🟠 | Settlements | ~~`open_settlement_request()` selected non-existent `expenses.created_by`~~ **FIXED** — every driver settlement initiation (and any expense posted while one was live) returned 500 `UndefinedColumn`. Found via production `error_logs` (id 285). | `db/queries/expenses.py::open_settlement_request` | ✅ 2026-08: dropped the phantom column from the SELECT (caller only checks existence); query live-verified against Neon. |
| B-12 | 🟠 | Analytics | ~~F-4 driver-leakage query joined on non-existent `e.created_by`~~ **FIXED** — `/api/v1/analytics/overview` returned 500. Found via production `error_logs` (id 286). | `api/v1/analytics.py` driver_leakage | ✅ 2026-08: attribution rerouted through the trip (`JOIN trips → users ON u.id = t.driver_user_id`); live-verified against Neon. |

## 2. Security & Reliability Risks

| ID | Sev | Risk | Detail | Recommendation |
|----|-----|------|--------|----------------|
| R-1 | 🔴 | ~~Ephemeral sessions~~ **DONE** | Auth sessions + login-lockout counters were process-local dicts: every deploy logged everyone out; >1 instance broke auth. | ✅ 2026-08: write-through Postgres mirror (`auth_sessions` + `login_throttle`, **token hashes only**) via `db/queries/auth_store.py`; cold tokens rehydrate from DB so restarts keep users logged in and instances share state; brute-force counters survive deploys. In-memory dicts stay the hot path; mirror writes are best-effort with a circuit breaker (2 strikes → 60 s skip) + `connect_timeout=10`. ⚠️ **Deploy action:** apply `database/incremental_ddl.sql`. |
| R-2 | 🟠 | ~~Connection-per-request~~ **DONE** | Fresh TCP+TLS to Neon per request (~50–150 ms overhead; burst storms). | ✅ 2026-08: lazy, thread-safe `SimpleConnectionPool(0, 10)` behind the same `get_db()` context-manager; broken/errored connections are discarded instead of recycled; `healthcheck` pooled too. Verified live against Neon. |
| R-3 | 🟠 | ~~No CI~~ **DONE** | `.github/` had only Copilot config; tests never ran automatically. | ✅ 2026-08: `.github/workflows/ci.yml` — backend job (ruff gate + pytest with dummy `DATABASE_URL`) + frontend build job, on push/PR/manual. Lint baseline cleaned first: 104 findings (87 auto-fixed; BOM+docstring order in `onboard.py`, unused var in `settlement.py`, `per-file-ignores` for `smoke_check.py` bootstrap). |
| R-4 | 🟡 | ~~Unpinned deps~~ **DONE** | All `>=` in requirements.txt — non-reproducible builds. | ✅ 2026-08: `requirements.lock` generated (93 pinned packages). Caveat: env-frozen snapshot incl. local dev tooling; adopt in CI deliberately or regenerate via `pip-compile`. `requirements.txt` stays the human-readable source. |
| R-5 | 🟡 | ~~Hardcoded CORS~~ **DONE** | Origins list was hardcoded in `main.py` incl. localhost. | ✅ 2026-08: env `CORS_ORIGINS` CSV → `settings.cors_origins`; historical allowlist kept as fallback. |
| R-6 | 🟡 | ~~PBKDF2 100k rounds~~ **DONE** | Was below OWASP's current ~600k guidance for PBKDF2-SHA256. | ✅ 2026-08: `_ITERATIONS = 600_000`; hash strings are self-describing (`pbkdf2_sha256$<iters>$…`) so existing credentials keep verifying unchanged. |
| R-7 | ⚪ | ~~No pagination~~ **DONE** | Every list endpoint returned full tables. | ✅ 2026-08: shared `deps._page_params()` — clamped `?limit=` (1–500) & `?offset=` (≥0), defaults 100/0 — wired through **trips, settlements, users, drivers, vehicles, fleets**. Responses stay byte-identical at current scale; SPA "load more" UI deferred until data volume demands it. |

## 3. Code-Quality & DX Enhancements

| ID | Item | Notes |
|----|------|-------|
| E-1 | ~~**Restore SPA 404 catch-all**~~ **DONE** | `path="*"` → new `pages/NotFound.jsx`, bare (no ProtectedRoute/Layout) — 2026-08. |
| E-2 | ~~**React ErrorBoundary**~~ **DONE** | `components/ErrorBoundary.jsx` wraps page content inside `<Layout>` — recoverable crash UI with Try again / Reload (2026-08). |
| E-3 | ~~**Route-level code splitting**~~ **DONE** | All pages `React.lazy`-loaded behind a Suspense shell — entry bundle dropped ~295→176 kB (-40%), pages are per-route chunks (2026-08). |
| E-4 | **Frontend test harness** | No Vitest/RTL configured. Start: `AuthContext`, `lib/api.js` 401 handling, one CRUD form-validation suite. |
| E-5 | ~~**Structured request logging**~~ **DONE** | `main.py` request-id middleware (honors inbound `X-Request-Id`, mints otherwise) → echoed as response header + persisted to new `error_logs.request_id` column (+ DDL in both schema files) for support-ticket correlation (2026-08). |
| E-9 | ~~**Shared API types**~~ **DONE** | `scripts/export_openapi.py` → `docs/openapi.json` (48 paths) + `npm run gen:api` (openapi-typescript) → committed `src/types/api.d.ts`. Regenerate both after any route/schema change; consumers adopt typed imports as the codebase moves toward TS. |
| E-6 | ~~**Dead config remnant**~~ **DONE** | `USER_PASSWORD` read removed from `config.py` (2026-08). |
| E-7 | ~~**Mobile sidebar UX**~~ **DONE** | ☰ hamburger drawer (aria-expanded toggle) replaces the always-stacked mobile nav card (2026-08). |
| E-8 | ~~**Accessibility pass**~~ **DONE (core)** | Global `:focus-visible` outline ring in `index.css`; icon-only controls carry `aria-label`s (bell, hamburger); nav uses real text labels. Deeper screen-reader passes remain ongoing hygiene. |
| E-9 | **Shared API types** | Generate TS types from FastAPI OpenAPI (`openapi-typescript`) → end stringly-typed payloads. |
| E-10 | **Sliding session renewal** | Warn ~15 min before the hard 72 h logout instead of an abrupt redirect mid-task. |

## 4. Product / UX Enhancements (existing surfaces)

| ID | Area | Status & notes |
|----|------|----------------|
| P-1 | Approvals | ✅ **DONE** — bulk select checkboxes + "Select pending" chip, bulk Approve/Deduct bar, keyboard shortcuts (**A** approve / **D** deduct / **Esc** clear) on the Expense Approvals feed (`TripWhatsApp.jsx`; reuses the existing per-expense action endpoint in a loop). |
| P-2 | Settlements | ✅ **DONE** — month filter + CSV export (UTF-8 BOM for Excel) in `SettledTrips.jsx`. *Deferred:* per-driver annual summary printout. |
| P-3 | Dashboard | ✅ **DONE** — new `GET /api/v1/dashboard/trends` (super_admin): 30-day spend-by-type + daily leakage trend, rendered as the "30-Day Trends" bars card. |
| P-4 | Vehicles | ✅ **DONE** — `insurance_expiry/puc_expiry/fitness_expiry` DATE columns (+ incremental DDL), API validation (`INVALID_DATE` on bad format), three date inputs in the Vehicle form. *Deferred:* list-row alert chips. |
| P-5 | Drivers | 🟡 **PARTIAL** — `users.licence_expiry` DATE column through driver API/form + ⚠ badge when ≤14 days out. *Deferred:* profile photo upload (needs storage decision). |
| P-6 | i18n | 🟡 **PARTIAL** — persisted HI/EN toggle (`vk_lang`) with 🌐 button translating all navigation chrome; page bodies remain bilingual-at-source. *Deferred:* full dictionary coverage. |

## 5. Feature Proposals

| # | Feature | Status & notes |
|---|---------|----------------|
| F-1 | **Phase C: real WhatsApp send + chat approvals** | ✅ **DONE (core)** — `services/whatsapp/send.py` (Graph API v20.0, failure-isolating); `POST /api/v1/whatsapp/send` live-sends `{"to","text"}`; webhook parses manager replies **`APPROVE/REJECT <expense_id>`** with role+ownership authorization (settlement acceptances stay app-only); driver notifications are direct service calls. **Deploy:** set `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_PHONE_ID`. *Optional next:* rich template messages/buttons. |
| F-2 | **Receipt OCR intake (Phase D)** | Kills driver typing errors; auto-fills amount/liters/odometer/rate. *Proposed* — `services/ocr/` package pre-scaffolded; multipart image on `POST /expenses` → vision extract → prefill with confidence score; low confidence routes to human review. Needs a vision-provider decision. |
| F-3 | **Notifications & digest center** | ✅ **DONE** — `GET /api/v1/notifications` derives alerts live from existing tables (`pending_approvals` >24h scoped to the caller, own-fleet TRIAL ending ≤3 days, settlement-ready count); 🔔 bell + badge + dropdown in the header (`NotificationBell.jsx`); nightly per-manager email digest = `cron_daily.py` step 3 via Resend (`dispatch_sync`, silent when unconfigured). Nothing persisted — zero schema cost. |
| F-4 | **Super-admin analytics page** | ✅ **DONE** — `GET /api/v1/analytics/overview` (top-10 vehicles by spend with ₹/km from odometer deltas, top-10 driver-wise leakage prevented, 6-month monthly spend) rendered on the new super-admin `/analytics` route (`pages/admin/Analytics.jsx`) with dependency-free bar charts + "Analytics" sidebar entry. |
| F-5 | **Driver payout run (payday batch)** | One-click monthly batta settlement per driver + printable payslip PDF. *Proposed* — aggregate `DRIVER_SALARY` rows + net balances from the unified ledger; extends the reportlab service. |
| F-6 | **Recurring trip templates** | ✅ **DONE** — `trip_templates` table (fleet-scoped, unique name) + `GET/POST/DELETE /api/v1/trip-templates` + "📋 Start from template" picker on NewTrip that pre-fills vehicle & driver. |
| F-7 | **Offline-first driver PWA** | Rural connectivity: queue receipts offline, background-sync later. *Proposed* — service worker + IndexedDB outbox; idempotency-key on `POST /expenses`. Largest effort item; needs a design pass. |
| F-8 | **Automation crons** | ✅ **DONE** — `scripts/cron_daily.py` (purge expired sessions + refresh live fuel benchmarks, snapshot-fallback) + `.github/workflows/cron.yml` scheduled 02:30 UTC daily (requires repo secret `DATABASE_URL`). Render Cron Job (`python scripts/cron_daily.py`) is an equivalent alternative. *Deferred:* document-expiry reminders (pairs P-4/F-3). |

## 6. Suggested Execution Order

1. ~~**R-3 CI pipeline**~~ ✅ **done 2026-08** — guards everything else
2. ~~**R-1 persistent sessions**~~ ✅ **done 2026-08** — deploy-stability blocker
3. ~~**B-1, B-2, B-3**~~ ✅ **done 2026-08** — auth/webhook security holes
4. ~~**R-2 connection pooling**~~ ✅ **done 2026-08** — perf win, low risk
5. ~~**E-1..E-3**~~ ✅ **done 2026-08** — SPA resilience/speed quick wins *(full E-batch closed: E-2/E-4/E-5/E-7/E-8/E-10 done, E-9 partial by design)*
6. **F-1 Phase C WhatsApp** ✅ **done 2026-08** — flagship feature (unblocked by B-2/B-3)
7. **P-1/P-2** ✅ **done 2026-08** — daily-user pain relief
8. Remaining: F-2, F-3 ✅, F-4 ✅, F-5, F-7 by business priority · E-4..E-10 · R-7

---
*Maintenance note: re-audit quarterly or after any auth/webhook/billing change; tick items off in-place and date the edits.*


