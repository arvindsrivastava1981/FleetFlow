# FleetFlow — Screen Flow Guide (Super Admin · Trip Manager · Driver)

Ground truth: `frontend/src/components/Layout.jsx` (sidebar + role filters) and
`frontend/src/App.jsx` (`<ProtectedRoute>` role guards). All pages call relative
`/api/v1/*` endpoints via `frontend/src/lib/api.js`.

## 1. Shared entry flow (all roles)

```
/login  ──POST /api/v1/auth/login──►  role resolved
   │                                    │
   ├── role = super_admin ─────────────►│
   ├── role = trip_manager ────────────►├──► /dashboard
   └── role = driver ──────────────────►│
                                        │
Fleet-less trip_manager (e.g. social sign-up)
   /dashboard ──► ProtectedRoute redirect ──► /onboarding (self-serve fleet wizard)
                                              └─ POST /api/v1/fleets/self-onboard → /dashboard
/change-password (any role) · Logout (sidebar → POST /api/v1/auth/logout)
```

## 2. Super Admin (`role = "super_admin"`)

**Sidebar sections:** Operations · Fleet & Assets · Settings (Rules & Rates) · Account

| Step | Screen | Next actions |
|---|---|---|
| 1 | `/dashboard` — platform KPIs, live dispatches | → Trips, Fleets, Analytics |
| 2 | `/trips` → `/trips/new` (pick vehicle + driver, or start from template) → `/trips/:tripCode` (log expenses, settle) | → `/settlements` |
| 3 | `/whatsapp` — Expense Approvals: approve/deduct flagged expenses | — |
| 4 | `/settlements` — settled trips + PDF export | — |
| 5 | `/fleets` — full CRUD: create firm, edit, toggle, plan/slots | → `/users` (per-fleet managers) |
| 6 | `/onboard` — Onboard Firm wizard (firm + owner + trial in one tx) | → new manager logs in |
| 7 | `/vehicles`, `/drivers` — CRUD incl. batta profile | feed New Trip dropdowns |
| 8 | `/benchmarks` — Rules & Rates, ★ favorites, live-rate sync (admin-only) | — |
| 9 | `/users` — user list, create manager/driver, toggle | — |
| 10 | `/analytics` — spend by vehicle, leakage prevented, 6-month trend | — |
| 11 | ~~`/subscription`~~ removed — super admin is fleet-less by design; per-fleet plans are managed via `/fleets` | — | — |

## 3. Trip Manager (`role = "trip_manager"`)

**Sidebar sections:** Operations · Fleet & Assets (incl. **My Fleet**, read-only) · Settings (Rules & Rates) · Account
(no Onboarding, no System & Reports). All data scoped to own `fleet_id` / `created_by`.

| Step | Screen | Next actions |
|---|---|---|
| 0 | First login without fleet → `/onboarding` wizard | → `/dashboard` |
| 1 | `/dashboard` — own KPIs + live dispatches | → `/trips/new` |
| 2 | `/trips` → `/trips/new` (own vehicles + active drivers) → `/trips/:tripCode` (expenses, settle) | → `/settlements` |
| 3 | `/whatsapp` — approve/deduct driver expense submissions (own fleet) | — |
| 4 | `/settlements` — own settled trips + PDFs | — |
| 5 | `/fleets` ("**My Fleet**") — read-only view of own firm; create/edit/toggle hidden | — |
| 6 | `/vehicles` — CRUD own vehicles | — |
| 7 | `/drivers` — CRUD + batta (FIXED_TRIP / PER_KM / DAILY / NONE) | — |
| 8 | `/benchmarks` — Rules & Rates (sync button hidden) | — |
| 9 | `/subscription` — own fleet's plan & vehicle slots | — |

## 4. Driver (`role = "driver"`)

**Sidebar sections:** Operations (limited) · Account. No Fleet & Assets, no admin pages.

| Step | Screen | Next actions |
|---|---|---|
| 1 | `/dashboard` — own trip count, expense status, financial summary | — |
| 2 | `/whatsapp` ("WhatsApp View") — submit/view own expenses, see approval/flag status | — |
| 3 | `/driver-salary` — read-only salary/batta view | — |
| 4 | `/settlements` — settled trips they drove + PDFs | — |

## 5. Role-guard matrix (sidebar vs backend)

| Route | super_admin | trip_manager | driver | Backend guard |
|---|---|---|---|---|
| `/fleets` | ✅ full CRUD | ✅ read-only (own fleet) | ❌ | GET: scoped to own fleet; `POST /fleets` also allows trip_manager (self-binds the new fleet, used by onboarding); PUT/toggle: super_admin only |
| `/trips`, `/trips/new`, `/trips/:code` | ✅ | ✅ | ❌ | `require_json_role("trip_manager","super_admin")` |
| `/vehicles`, `/drivers`, `/benchmarks` | ✅ | ✅ | ❌ | role-guarded |
| `/users`, `/onboard`, `/analytics` | ✅ | ❌ | ❌ | super_admin only |
| `/driver-salary` | ❌ | ❌ | ✅ | driver only |
| `/subscription` | ❌ (fleet-less by design — plans managed via `/fleets`) | ✅ (own fleet's plan & slots) | ❌ | backend allows both manager roles; SPA route + sidebar are trip_manager-only |
| `/whatsapp`, `/settlements`, `/dashboard`, `/change-password` | ✅ | ✅ | ✅ (scoped) | any authenticated |
