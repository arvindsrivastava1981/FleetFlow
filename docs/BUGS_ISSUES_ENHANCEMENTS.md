# VahanKhata — Bugs, Issues, Enhancements & Feature Roadmap

> **Generated:** 2026-08 · **Method:** Full-stack audit (auth/session flow, webhook handlers,
> DB access layer, billing idempotency, trip lifecycle, SPA routing/state) after the 2026-08
> dead-code cleanup. Every bug cites file + line evidence.
> Severity: 🔴 Critical · 🟠 High · 🟡 Medium · ⚪ Low.

---

## 1. Bugs & Verified Defects

| ID | Sev | Area | Finding | Evidence | Fix sketch |
|----|-----|------|---------|----------|------------|
| B-1 | 🟠 | Auth | ~~Deactivated/password-changed users keep access up to 72 h~~ **FIXED** | `core/security.py`, `api/v1/auth.py`, `api/v1/users.py` | ✅ 2026-08: new `revoke_user_sessions()` — called on change-password and on user/driver deactivation toggles; live tokens die instantly. SPA signs out locally after a password change. (Per-process until R-1 lands.) |
| B-2 | 🟠 | WhatsApp | ~~Inbound webhook accepts unsigned payloads~~ **FIXED** | `api/v1/whatsapp.py::_signature_valid` + POST handler | ✅ 2026-08: `X-Hub-Signature-256` HMAC verified before parsing/routing (401 on mismatch). Active whenever env `WHATSAPP_APP_SECRET` is set. ⚠️ **Deploy action: add `WHATSAPP_APP_SECRET` to Render env.** |
| B-3 | 🟠 | WhatsApp | **`POST /api/v1/whatsapp/send` is unauthenticated** (no auth/role guard). Today a no-op stub; the moment Phase-C credentials land it becomes an open relay. | `api/v1/whatsapp.py:149-160`; ends in `TODO(Phase C)` | Guard with `require_json_role("trip_manager","super_admin")` *before* live send ships. |
| B-4 | 🟡 | Trips | ~~Trip-code race~~ **FIXED** | `db/queries/trips.py::insert_trip` | ✅ 2026-08: `pg_advisory_xact_lock(hashtext(vehicle_no))` taken before code generation — auto-releases on commit/rollback, serializes across instances, no retry loop needed. |
| B-5 | 🟡 | Ops | ~~`/healthz` leaks raw DB error text~~ **FIXED** | `db/connection.py::healthcheck` | ✅ 2026-08: returns generic `{"db":"error"}`; detail only via `logging.exception`. |
| B-6 | 🟡 | Auth | ~~Session cookie lacks `secure` flag~~ **FIXED** | `api/v1/auth.py` set_cookie | ✅ 2026-08: `secure=settings.cookie_secure` (env `COOKIE_SECURE`, default ON; localhost exempt). |
| B-7 | ⚪ | Auth | ~~Cookie transport redundant~~ **DONE** | `config.py`, `api/v1/auth.py`, `core/security.py` | ✅ 2026-08: cookie issuance now opt-in via env `AUTH_COOKIE=1` (default off — SPA is Bearer-only). Bonus fix: `destroy_session` revokes the **Bearer** token too — logout previously left server-side sessions alive until TTL. |
| B-8 | ⚪ | Billing | ~~Webhook dedupe bypassed when `event_id` empty~~ **FIXED** | `api/webhook.py` | ✅ 2026-08: missing ids fall back to a `sha256:<body>` content hash so dedupe always applies; guard simplified. |
| B-9 | ⚪ | Escalations | ~~Escalation callback URL built from request scheme/netloc~~ **FIXED** | `api/v1/expenses.py` (driver notification) | ✅ 2026-08: uses `settings.app_public_url` when set, request fallback otherwise. Note: this hop is auth-gated since B-3 — Phase C must call the sender service directly. |
| B-10 | ⚪ | Repo hygiene | ~~Stray `settlement_debug.log`~~ removed; sample PDF still git-tracked (README links it). | root listing; README:31 | ✅ Partial 2026-08: log deleted. To untrack the PDF yourself: `git rm --cached FleetFlow_Sample_Settlement_Sheet.pdf` (no code references it). |

## 2. Security & Reliability Risks

| ID | Sev | Risk | Detail | Recommendation |
|----|-----|------|--------|----------------|
| R-1 | 🔴 | ~~Ephemeral sessions~~ **DONE** | Auth sessions + login-lockout counters were process-local dicts: every deploy logged everyone out; >1 instance broke auth. | ✅ 2026-08: write-through Postgres mirror (`auth_sessions` + `login_throttle`, **token hashes only**) via `db/queries/auth_store.py`; cold tokens rehydrate from DB so restarts keep users logged in and instances share state; brute-force counters survive deploys. In-memory dicts stay the hot path; mirror writes are best-effort with a circuit breaker (2 strikes → 60 s skip) + `connect_timeout=10`. ⚠️ **Deploy action:** apply `database/incremental_ddl.sql`. |
| R-2 | 🟠 | ~~Connection-per-request~~ **DONE** | Fresh TCP+TLS to Neon per request (~50–150 ms overhead; burst storms). | ✅ 2026-08: lazy, thread-safe `SimpleConnectionPool(0, 10)` behind the same `get_db()` context-manager; broken/errored connections are discarded instead of recycled; `healthcheck` pooled too. Verified live against Neon. |
| R-3 | 🟠 | ~~**No CI**~~ **DONE** | `.github/` had only Copilot config; tests never ran automatically. | ✅ 2026-08: `.github/workflows/ci.yml` — backend job (ruff gate + pytest with dummy `DATABASE_URL`) + frontend build job, on push/PR/manual. Lint baseline cleaned first: 104 findings (87 auto-fixed; BOM+docstring order in `onboard.py`, unused var in `settlement.py`, `per-file-ignores` for `smoke_check.py` bootstrap). |
| R-4 | 🟡 | ~~Unpinned deps~~ **DONE** | All `>=` in requirements.txt — non-reproducible builds. | ✅ 2026-08: `requirements.lock` generated (93 pinned packages). Caveat: it is an env-frozen snapshot that includes local dev tooling; adopt it in CI deliberately or regenerate via `pip-compile`. `requirements.txt` stays the human-readable source. |
| R-5 | 🟡 | ~~Hardcoded CORS~~ **DONE** | Origins list was hardcoded in `main.py` incl. localhost. | ✅ 2026-08: env `CORS_ORIGINS` CSV → `settings.cors_origins`; historical allowlist kept as fallback. |
| R-6 | 🟡 | ~~PBKDF2 100k rounds~~ **DONE** | Was below OWASP's current ~600k guidance for PBKDF2-SHA256. | ✅ 2026-08: `_ITERATIONS = 600_000`; hash strings are self-describing (`pbkdf2_sha256$<iters>$…`) so existing credentials keep verifying unchanged. |
| R-7 | ⚪ | No pagination | Every list endpoint returns full tables. | `?limit=&offset=` envelope + frontend load-more. |

## 3. Code-Quality & DX Enhancements

| ID | Item | Notes |
|----|------|-------|
| E-1 | ~~**Restore SPA 404 catch-all**~~ **DONE** | `path="*"` → new `pages/NotFound.jsx`, bare (no ProtectedRoute/Layout) — 2026-08. |
| E-2 | **React ErrorBoundary** | Any render crash = white screen. Wrap `<Layout>` children with retry/reload UI. |
| E-3 | **Route-level code splitting** | Single ~280 KB bundle; `React.lazy` per route cuts initial JS substantially. |
| E-4 | **Frontend test harness** | No Vitest/RTL configured. Start: `AuthContext`, `lib/api.js` 401 handling, one CRUD form-validation suite. |
| E-5 | **Structured request logging** | request-id middleware → `error_logs.request_id` + `X-Request-Id` response header for support tickets. |
| E-6 | ~~**Dead config remnant**~~ **DONE** | `USER_PASSWORD` read removed from `config.py` (2026-08). |
| E-7 | **Mobile sidebar UX** | Sub-1024 px stacks the whole nav above content; switch to a hamburger drawer. |
| E-8 | **Accessibility pass** | Emoji-only icons lack accessible names; add `aria-label`s + visible focus rings on `.btn-*`. |
| E-9 | **Shared API types** | Generate TS types from FastAPI OpenAPI (`openapi-typescript`) → end stringly-typed payloads. |
| E-10 | **Sliding session renewal** | Warn ~15 min before the hard 72 h logout instead of an abrupt redirect mid-task. |

## 4. Product / UX Enhancements (existing surfaces)

| ID | Area | Enhancement |
|----|------|-------------|
| P-1 | Approvals | Bulk approve/reject + keyboard shortcuts on the Expense Approvals feed (`/whatsapp`). |
| P-2 | Settlements | Month/date-range filter + CSV export; per-driver annual summary printout. |
| P-3 | Dashboard | Super-admin trends (30-day spend by exp_type, leakage-prevented trend) — ledger already supports it. |
| P-4 | Vehicles | Document vault: insurance/PUC/fitness expiry dates + red-banner alerts 14 days out. |
| P-5 | Drivers | Self-service profile photo + licence-expiry field surfaced in `/drivers`. |
| P-6 | i18n | Formalize existing bilingual labels (`label_en`/`label_hi`) into a persisted HI/EN toggle. |

## 5. New Feature Proposals (prioritized)

| # | Feature | Value | Effort | Sketch |
|---|---------|-------|--------|--------|
| F-1 | **Phase C: real WhatsApp send + chat approvals** ✅ **DONE (core)** | Closes the loop for low-smartphone drivers; approvals happen inside chat. | M | ✅ 2026-08: `services/whatsapp/send.py` (Graph API v20.0, failure-isolating); `POST /api/v1/whatsapp/send` now live-sends (`to`+`text`); webhook parses manager replies **`APPROVE/REJECT <expense_id>`** with full role+ownership authorization (settlement acceptances stay app-only); driver notifications are direct service calls. **Deploy:** set `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_PHONE_ID`. *Optional next:* rich template messages/buttons. |
| F-2 | **Receipt OCR intake (Phase D)** | Kills driver typing errors; auto-fills amount/liters/odometer/rate. | M-L | `services/ocr/` package is pre-scaffolded; multipart image on `POST /expenses` → vision extract → prefill with confidence score; low confidence routes to human review. |
| F-3 | **Notifications & digest center** | Owners hear about flagged expenses/expiring trials without living in the app. | M | In-app bell + nightly Resend email digest: approvals pending >24 h, trial ending ≤3 days, settlement-ready count. Underlying tables already exist. |
| F-4 | **Super-admin analytics page** | Cost/km per vehicle, driver-wise leakage prevented, monthly heatmap — turns the audit ledger into a sales asset. | M | Read-only aggregate endpoint over `expenses`+`trips`; the removed KPI SQL scaffolds are a proven starting point. |
| F-5 | **Driver payout run (payday batch)** | One-click monthly batta settlement per driver + printable payslip PDF. | M | Aggregate `DRIVER_SALARY` rows + net balances from the unified ledger; extends the reportlab service. |
| F-6 | **Recurring trip templates** ✅ **DONE** | Daily routes become one tap on `/trips/new`. | S | ✅ 2026-08: `trip_templates` table (fleet-scoped, unique name) + `GET/POST/DELETE /api/v1/trip-templates` + "📋 Start from template" picker on NewTrip that pre-fills vehicle & driver. |
| F-7 | **Offline-first driver PWA** | Rural connectivity: queue receipts offline, background-sync later. | L | Service worker + IndexedDB outbox; idempotency-key on `POST /expenses`. |
| F-8 | **Automation crons** ✅ **DONE** | Daily housekeeping without manual clicks. | S-M | ✅ 2026-08: `scripts/cron_daily.py` (purge expired sessions + refresh live fuel benchmarks, snapshot-fallback) + `.github/workflows/cron.yml` scheduled 02:30 UTC daily (requires repo secret `DATABASE_URL`). Render Cron Job (`python scripts/cron_daily.py`) is an equivalent alternative. *Deferred:* document-expiry reminders (pairs P-4/F-3). |

## 6. Suggested Execution Order

1. ~~**R-3 CI pipeline**~~ ✅ **done 2026-08** — guards everything else
2. ~~**R-1 persistent sessions**~~ ✅ **done 2026-08** — deploy-stability blocker
3. ~~**B-1, B-2, B-3**~~ ✅ **done 2026-08** — auth/webhook security holes
4. ~~**R-2 connection pooling**~~ ✅ **done 2026-08** — perf win, low risk
5. **E-1..E-3** — SPA resilience/speed quick wins
6. **F-1 Phase C WhatsApp** — flagship feature (unblocked by B-2/B-3)
7. **P-1/P-2** — daily-user pain relief
8. Remaining features by business priority

---
*Maintenance note: re-audit quarterly or after any auth/webhook/billing change; tick items off in-place and date the edits.*


