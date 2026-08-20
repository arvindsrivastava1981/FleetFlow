# API Spec Audit — Discrepancies

This document lists only the deviations found when auditing the codebase
(`backend/app/api/v1/*.py`, `backend/app/api/webhook.py`, `backend/app/main.py`)
against the FleetFlow/VahanKhata API specification. Everything not listed here
matches the spec.

## Legend

- ⚠️ Partial / nuance
- ❌ Gap

---

## ⚠️ Partial / nuance

### Auth envelope — only `login` and `me` are unwrapped
- Spec: "auth … omit the wrapper."
- Code: `POST /auth/login` and `GET /auth/me` omit the `data` envelope, but
  `POST /auth/logout` (`Data[LogoutResult]`) and `POST /auth/change-password`
  (`Data[ChangePasswordResult]`) **are** wrapped. (`auth.py`)

### WhatsApp escalation feed lives in `expenses.py`
- Spec: `/api/v1/whatsapp/escalations` belongs to the WhatsApp bot domain.
- Code: served at `/api/v1/whatsapp/escalations` but physically defined in
  `expenses.py` (role-guarded `trip_manager`/`super_admin`). Functionally
  correct; only the file organization differs.

### Vehicle toggle path is `/vehicles/{vid}/toggle`, not bare `/vehicles/{vid}`
- Spec: "toggle active states … (`/api/v1/vehicles/{vid}`)."
- Code: the toggle route is `POST /api/v1/vehicles/{vid}/toggle`; the bare
  `PUT /vehicles/{vid}` is the *update* route. A spec-text imprecision, not a
  code gap. (`vehicles.py`)

### Fleet plan-tier assignment has no fleet-scoped endpoint
- Code: plan activation flows through `/billing/subscribe` and the Razorpay
  webhook (`webhook.py`), not a dedicated fleet endpoint. (`billing.py`,
  `webhook.py`)

### WhatsApp `/send` is a documented no-op stub
- Code: `POST /api/v1/whatsapp/send` returns
  `{sent: false, reason: "not_wired"}` until `WHATSAPP_ACCESS_TOKEN` /
  `WHATSAPP_PHONE_ID` are wired; matches the spec's "fire-and-forget fallback
  if token absent." (`whatsapp.py`)

---

## ❌ Gap

### 1. No "adjust" action on expense manager actions
- Spec: managers may "approve, reject, or **adjust** individual expense items."
- Code: `POST /expenses/{expense_id}/action` accepts only `APPROVE` / `REJECT`
  (`expenses.py:162`). `action_expense_status` only maps to `APPROVED` /
  `REJECTED`; there is no `ADJUST` action or `adjust_amount` handling anywhere
  in the codebase. (`expenses.py`)

### 2. No hard-delete endpoints for fleet / vehicle / user
- Spec: "CRUD operations on fleets."
- Code: only Create/Read/Update plus soft toggle (`/toggle` =
  deactivate/reactivate). No `DELETE` routes exist for `fleets`, `vehicles`,
  or `users`. (`fleets.py`, `vehicles.py`, `users.py`)

### 3. No `GET /fleets/{fid}` detail read
- Spec: fleet management CRUD.
- Code: there is no plain `GET /fleets/{fid}` resource view; only
  `GET /fleets/{fid}/billing` (super-admin billing-health panel) exists.
  (`fleets.py`)