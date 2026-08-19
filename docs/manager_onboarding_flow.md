# Manager Onboarding Flow — Super Admin → First Trip

> End-to-end flow for how a **Super Admin** onboards a **Trip Manager** and gets them from
> subscription to their first created trip. Every step maps to a real route in
> `backend/app/api/v1/`; actor and persistence side-effects are annotated.
>
> **Keystone concept (from the code):** everything is anchored on the **`fleets`**
> row, which owns the subscription entitlement (trial clock, `vehicle_limit`,
> Razorpay billing refs). A Trip Manager is bound to **one fleet** via
> `users.fleet_id`, and vehicles/trips resolve to that fleet at runtime.

---

## Phase 0 — Prerequisites (Super Admin owns these)

| Data | Lives in | Notes |
|---|---|---|
| `subscription_plans` | `database/schema.sql` (seeded) | TRIAL = 15d / ₹0 / 1 veh · MONTHLY = ₹799 / 1 · YEARLY = ₹7,191 (25% off) / 1 |
| `fleets` rows | `fleets` table | `owner_name`, `phone` (**UNIQUE**), `email`, `plan`, `vehicle_limit`, `subscription_status` |
| Fleet CRUD | `POST/PUT/toggle /api/v1/fleets` | **Only Super Admin** can update / toggle a fleet |
| `fuel_benchmarks` | `/benchmarks` page | Super Admin-only. Drives rule-engine fuel banding |
| Rule cards / constants | `/rule-engine` | TRIAL/ACTIVE gating + price constants |

---

## Phase 1 — Create the Fleet (if the manager has none)

**Actor:** Super Admin · **Route:** `POST /api/v1/fleets` (`fleets.py::api_create_fleet`)

1. Validate `owner_name` + `phone` → duplicate phone = `409 DUP_PHONE`.
2. `insert_fleet(owner_name, phone, email, plan)` (default `subscription_plan` = `MONTHLY`).
3. **Persisted:** `fleets.subscription_status` = `TRIAL`, `vehicle_limit` set, trial clock.
4. (Managers may later self-create a fleet — the code **re-binds their `fleet_id` in-place** — but the onboarding path here is the Super Admin doing it.)

---

## Phase 2 — Create the Trip Manager user (binds to fleet + starts trial)

**Actor:** Super Admin · **Route:** `POST /api/v1/users` (`users.py::api_create_user`, guard `require_json_role("super_admin")`)

1. Validate `username`, `full_name`, `role="trip_manager"`, `password` (must be in `VALID_ROLES`).
2. Because `role == "trip_manager"`:
   - Resolve **default fleet** → `manager_fleet_id`.
   - If that fleet is **not entitled** (e.g. stale TRIAL with no clock), call `start_trial_subscription(...)` → **15-day trial starts** so the manager can immediately register a vehicle.
3. `create_user(..., fleet_id=manager_fleet_id, ...)` → `users.fleet_id` bound, role stored.
4. If `email` provided → **manager onboarding email** with temporary password + login URL (`send_manager_onboarding_email_sync`).
5. Returns `200 {"id": <new_id>}`.

---

## Phase 3 — Manager activates the subscription (entitlement)

**Actor:** Trip Manager (login → `/login`, then `/billing`) · roles `trip_manager` / `super_admin`

| Step | Route | Effect |
|---|---|---|
| View state | `GET /api/v1/billing/overview` | `subscription_status`, `vehicle_count/limit`, plans |
| Activate **TRIAL** | `POST /api/v1/billing/subscribe` `{plan_code:"TRIAL"}` | `start_trial_subscription()` → `{redirect_url:"/fleets", trial:true}`. No payment. 15d / 1 veh |
| Activate **paid** | `.../subscribe` `{plan_code:"MONTHLY"|"YEARLY"}` | Razorpay customer + payment link → `redirect_url` for checkout |
| Extra vehicle slot | `POST /api/v1/billing/vehicle-slot` | Extra Razorpay link for the next vehicle (1 per slot) |

**Payment completion:** Razorpay webhook → `backend/app/api/webhook.py` →
`set_plan_subscription()` / `set_yearly_subscription()` sets `subscription_status = 'ACTIVE'`,
updates `vehicle_limit` and `next_billing_date` (+1 / +12 months).

> **Hard dependency (§ G3 gaps):** until the fleet is **ACTIVE** or on a **running** TRIAL,
> `_vehicle_limit_ok` returns `false` → vehicle create fails with `402 VEHICLE_LIMIT`.

---

## Phase 4 — Register the vehicle(s)

**Actor:** Trip Manager / Super Admin · **Route:** `POST /api/v1/vehicles` (`vehicles.py::api_create_vehicle`, `require_json_role("trip_manager","super_admin")`)

1. Resolve tenant fleet via `get_user_fleet_id(manager)` (the bound fleet).
2. `_vehicle_limit_ok` → fleet must be **ACTIVE or running-TRIAL**, and `count_active_vehicles < vehicle_limit`.
3. Validate plate against `^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$` (shared `_PLATE_RE`).
4. `insert_vehicle(...)` with `fleet_id`, `created_by=manager`. → `201 {"id": …}`
5. Repeat until capacity; buy extra slots in Phase 3 as needed.

---

## Phase 5 — Onboard the driver (with batta profile)

**Actor:** Trip Manager / Super Admin · **Route:** `POST /api/v1/drivers` (`users.py::api_create_driver`)

1. Validate `username`, `full_name`, `password`.
2. `create_user(..., role="driver", batta_type=FIXED_TRIP|PER_KM|DAILY|NONE, default_batta_rate)`.
3. **Note:** drivers are *not* force-bound to the manager's fleet (regression-guarded by `test_create_driver_is_not_bound_to_fleet`) — the trip binding is what matters. Returns `201 {"id": …}`.

> Batta is resolved at **trip-creation time** via `get_driver_batta_profile` + `resolve_trip_batta`.

---

## Phase 6 — Create the first trip

**Actor:** Trip Manager / Super Admin · **Route:** `POST /api/v1/trips` (`trips.py::api_create_trip`, `require_json_role("trip_manager","super_admin")`)

1. Guard: role must be `trip_manager` / `super_admin`.
2. Validate payload:
   - `vehicle_no` required + matches plate regex → else `400 INVALID_PLATE`
   - `driver_name` required
   - `advance_amount >= 0`, `start_odo >= 0`
   - `driver_phone` valid **10-digit** (starts `6`-`9`, length 10) → `400 INVALID_PHONE`
3. Resolve tenant: `_resolve_trip_fleet(user)` = `users.fleet_id`, fallback default fleet → none = `400 NO_FLEET`.
4. **One active trip per fleet:** `active_trip_exists(conn, fleet_id)` → `409 ACTIVE_TRIP_EXISTS`.
5. `get_driver_batta_profile(driver_user_id)` → `driver_batta_amount = resolve_trip_batta(...)`.
6. `insert_trip(fleet_id, vehicle_no, driver_name, driver_phone, advance_amount, start_odo, created_by=manager, driver_user_id, vehicle_id, driver_batta_amount)`.
7. → **`201 {"trip_code": "…", "status": "ACTIVE"}`** ✅ live.

**Operational loop follows:** driver submits fuel/expense receipts (`/api/v1/expenses` via WhatsApp simulator) → manager approves/deducts (`/expenses/{id}/action`) → settlement computed → **`POST /api/v1/trips/{code}/settle`** (no pending expenses) → settled PDF.

---

## End-to-end sequence (actors + routes)

```
SUPER ADMIN                          FLEET  (subscription entitlement)
   │  POST /fleets ──────────────────────► creates fleet, starts TRIAL clock
   │  POST /users {role:"trip_manager"} ──► binds users.fleet_id, refreshes trial
   ▼
TRIP MANAGER                          (login → /billing)
   │  GET  /billing/overview
   │  POST /billing/subscribe   TRIAL | MONTHLY | YEARLY
   │      │  Razorpay link ──► paid ──► webhook ──► fleets.status=ACTIVE
   │  POST /billing/vehicle-slot        (optional extra vehicles)
   ▼
   │  POST /vehicles  ──► _vehicle_limit_ok (needs ACTIVE/TRIAL + capacity)
   │  POST /drivers   ──► driver + batta profile
   ▼
   │  POST /trips ──► plate/+91/advance/odo → no concurrent ACTIVE
   │                   → resolve tenant → resolve batta
   ▼
   ✅ 201 { trip_code, status: ACTIVE } → expenses → settle → PDF
```
## Identified Gaps & Recommended Fixes

### G1 — Fleet picker missing at manager creation (highest impact) 🔴
`api_create_user` always binds a new `trip_manager` to the **default** fleet only. With multiple fleets there is no way to target a specific one at this step.

**Fix (backend):** accept optional `fleet_id` in `POST /users` body when `role == "trip_manager"`; verify it exists/is active, use it in place of `_resolve_default_fleet_id`, keep default-fleet as fallback.

**Fix (frontend):** add `fleet_id` select (from `GET /api/v1/fleets`) to the `Users.jsx` create form (Super Admin-only).

**Fix (data model, optional):** add `default_fleet_id` on `users` so a manager points at a non-default fleet explicitly.
---

## Implementation status (completed with "fleet = transport firm" model)

> All of the following changes have been **implemented and are covered by tests**
> (`tests/unit/test_onboarding_entitlements.py`, plus the pre-existing
> `tests/unit/test_new_manager_vehicle.py` which is green).

### Data model
- `subscription_plans.features` JSONB capability matrix (seed values provided).
- `fleets.is_default` anchor + `fleets.entitlement_addons` JSONB.
- `users.fleet_role` (owner/manager/branch_head/driver).
- New `fleet_billing_events` audit table (PLAN_CHANGE / EXTRA_SLOT / TRIAL_START / PAYMENT).
- All additions are **idempotent** in `schema.sql` and `incremental.sql` (drop-safe, no removed columns).

### Services & routes
- **`backend/app/services/entitlements.py`** — single entitlement resolver
  (`fleet_feature()`) + vehicle gate (`fleet_can_add_vehicles()`) producing
  distinct `NOT_ENTITLED` vs `VEHICLE_LIMIT` reasons (fixes G3).
- **`POST /api/v1/fleets/onboard`** (`onboard.py`) — transactional onboarding
  wizard: fleet + owner manager + trial (+ optional vehicle/driver), returns
  inline `payment_url` for paid plans (fixes G2, inline subscription).
- **`POST /api/v1/users`** — optional `fleet_id` picker for `trip_manager`
  creation (fixes G1).
- **`GET /api/v1/fleets/{fid}/billing`** — Super Admin billing/entitlement
  health view incl. audit ledger (fixes G6).
- `log_fleet_billing_event` / `get_fleet_billing_events` query helpers.

### Status of the earlier gap list
| Gap | Status |
|---|---|
| G1 fleet picker | ✅ implemented |
| G2 onboarding wizard | ✅ implemented |
| G3 entitlement-reason clarity | ✅ implemented (NOT_ENTITLED vs VEHICLE_LIMIT) |
| G4 trip cancel API | ⏭ not implemented (recommended next) |
| G5 default-fleet anchor | ✅ `fleets.is_default` added (routing favour pending) |
| G6 billing health view | ✅ implemented |
| G7 tenant-isolation fallback | 🟡 partially (is_default added; fallback removal recommended) |
| G8 email audit | ⏭ not implemented |
| G9 trial-restart cap | ⏭ not implemented |
| G10 billing/slot ledger | ✅ `fleet_billing_events` added + queried |

### Suggested next steps
- **G4** `POST /api/v1/trips/{code}/cancel` to release the one-active-trip lock.
- **G5/G7** wire `is_default` into `get_default_fleet`/`_resolve_*_fleet` so
  manager-creation & vehicle/trip/billing never silently fall back to the first
  active fleet.
- **G8** record onboarding-email outcome on `users.onboarding_email_at`.

### G2 — No transactional "onboarding wizard" 🔴
Phase 1–5 are five separate manual calls; a Super Admin must know the order, and there's no atomic "one-shot" path.

**Fix:** add `POST /api/v1/fleets/onboard` (Super Admin-only) that, in **one transaction**: create fleet → create manager user bound to it → start trial → optionally seed first vehicle + driver → return all ids + onboarding context. Frontend: collapse to a `/onboard/manager` wizard, keep the CRUD endpoints for compat.

### G3 — Silent `402 VEHICLE_LIMIT` (no reason) 🔴
`_vehicle_limit_ok` throws the same `402 VEHICLE_LIMIT` whether it's "not entitled" or "capacity reached".

**Fix:** return a machine-readable code from `_vehicle_limit_ok` — `NOT_ENTITLED` vs `VEHICLE_LIMIT` — and surface a "starts subscription" CTA in the UI for `NOT_ENTITLED`. (Keeps the gate; adds clarity.)

### G4 — "One active trip per fleet" friction 🔴
`active_trip_exists` blocks a second trip; no way to release a stale ACTIVE one.

**Fix:** add `POST /api/v1/trips/{code}/cancel` (Super Admin / owning manager) that moves a stale ACTIVE trip to `CANCELLED` and releases the lock; show the blocking trip on `/trips/new`.
### G5 — No `default` anchor on fleets 🔴
`get_default_fleet` returns *first active fleet*; with no fleet or multiple actives, onboarding can route to the wrong tenant or `400 NO_FLEET`.

**Fix:** add `is_default` boolean on `fleets`, guarantee exactly one default, and make manager creation fail loudly (`400 NO_FLEET`) when a specific fleet was requested but none resolves.

### G6 — No per-fleet billing health view for Super Admin 🟡
`GET /api/v1/fleets` shows plan/status but not trial-vs-consumed, next billing, slot usage.

**Fix:** add `GET /api/v1/fleets/{fid}/billing` (Super Admin) returning `subscription_status`, `vehicle_limit`, `active_vehicle_count`, `trial_started_at`/`trial_ends_at`, `next_billing_date`, last webhook event.

### G7 — Multi-tenant default-fleet collisions 🟡
`_resolve_*_fleet` fans out to the **default** fleet when `fleet_id` is empty → two managers silently share a fleet and hit its cap together.

**Fix (with G1/G5):** remove default-fleet fallback from vehicle/trip/billing resolution; use the bound `fleet_id` or fail with `NO_FLEET`/`NOT_ENTITLED`.

### G8 — Onboarding email is fire-and-forget 🟡
`send_manager_onboarding_email_sync` is best-effort; a failed send is silent.

**Fix:** record `onboarding_email_at`/last error on `users`, expose it on the Users page, add a "re-send welcome" action.

### G9 — Trial restarts are unbounded 🟡
`start_trial_subscription` restarts the 15-day trial on every manager create without a counter.

**Fix:** add `trial_start_count` / `last_trial_started_at` on `fleets`; disallow auto-restart > N times, else force the purchase path.

### G10 — No per-fleet billing/slot ledger 🟡
Extra slots are purchased but there's no history of plan baseline vs bought slots.

**Fix:** add a `fleet_billing_events` ledger (event type, plan_code, amount, razorpay ref, created_at) replayed in the billing overview; the webhook appends rows.

---

### Priority cheat-sheet
| Priority | Gap | Impact if unfixed |
|---|---|---|
| 🔴 P0 | G1 fleet picker · G2 onboarding wizard · G3 entitlement-reason clarity | Manual/ambiguous multi-fleet onboarding; opaque vehicle block |
| 🔴 P1 | G5 default-fleet anchor · G7 tenant isolation | Wrong-tenant / `NO_FLEET` routing |
| 🟡 P2 | G4 cancel API · G6 billing health · G9 trial cap · G10 slot ledger | Ops friction, muted audit |
| 🟡 P3 | G8 email retry/audit | Missed welcomes go unnoticed |

> **Suggested starting point:** implement **G1 (fleet picker)** first — smallest change, most
> impact, covered by the existing `test_new_manager_vehicle.py` regression pattern, and it
> unblocks G2 / G5 / G7. Then wrap the flow in `POST /fleets/onboard` (G2) and layer on the
> error-clarity (G3) + billing-health (G6) views.