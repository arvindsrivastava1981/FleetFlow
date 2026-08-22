---

# 📦 Installation & Quickstart

**FleetFlow** is three apps in one repo:

| App | Stack | Folder | Local URL | Env file |
|-----|-------|--------|-----------|----------|
| **Backend API** | FastAPI (Python 3.12) · Neon Postgres | `backend/` | http://localhost:10000 | `backend/.env` |
| **App SPA** | React 18 + Vite | `frontend/` | http://localhost:5173 | `frontend/.env` |
| **Marketing site** | React 18 + Vite | `public-site/` | http://localhost:5174 | `public-site/.env` |

No ORM, no Alembic — the schema is applied manually from `database/schema.sql`.
Config is **env-driven and fail-fast**: the backend refuses to boot without
`DATABASE_URL`. Every folder ships a ready-to-copy **`.env.example`**.

> 💡 All `.env` files are git-ignored. Commit only the `.env.example` templates.

---

## 1. Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.12+ | `python --version` |
| Node.js | 18+ (20 recommended) | `node --version` |
| PostgreSQL | Neon managed DB (or local 14+) | your DSN ready |
| psql CLI | any (optional — only to apply the schema) | `psql --version` |

---

## 2. Apply the database schema (once)

The app **never** runs DDL. From the repo root:

```powershell
# Fresh install
psql "$env:DATABASE_URL" -f database/schema.sql

# Already installed? Apply idempotent additions instead (sessions, throttle,
# doc/licence dates, trip templates, request-id column…):
psql "$env:DATABASE_URL" -f database/incremental_ddl.sql
```

---

## 3. Backend API

```powershell
# 3a. Virtual env + deps (repo root)
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 3b. Environment
Copy-Item backend\.env.example backend\.env
notepad backend\.env                   # set DATABASE_URL (required)
```

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | ✅ | Neon Postgres DSN (`sslmode=require`) |
| `CORS_ORIGINS` | – | CSV override; defaults cover prod + Vite dev |
| `COOKIE_SECURE` / `AUTH_COOKIE` | – | cookie flags; both default off/safe for local |
| `RESEND_API_KEY` / `SENDER_EMAIL` / `SUPPORT_EMAIL` / `APP_PUBLIC_URL` | – | email + digest (F-3) |
| `WHATSAPP_ACCESS_TOKEN` / `WHATSAPP_PHONE_ID` / `WHATSAPP_APP_SECRET` / `WEBHOOK_VERIFY_TOKEN` | – | Phase C bot + webhook signature checks (B‑2/F‑1) |
| `RAZORPAY_API_KEY` / `_SECRET` / `_WEBHOOK_SECRET` / `_TEST_MODE` | – | billing |

> Loading order: repo-root `.env` is read first (legacy), then `backend/.env`
> **overrides** it — so either location works during migration.

```powershell
# 3c. Run (pick ONE)
uvicorn backend.app.main:app --host 0.0.0.0 --port 10000 --reload   # direct
powershell -File start.ps1 -CheckOnly                               # validate install
powershell -File start.ps1                                          # validate + start

Open http://localhost:10000/docs        # interactive OpenAPI
```

---

## 4. Frontend SPA

```powershell
cd frontend
Copy-Item .env.example .env             # keep VITE_API_BASE_URL empty for dev
npm install
npm run dev                             # → http://localhost:5173
```

The Vite dev server proxies `/api/*` → `http://localhost:10000`, so the SPA
talks to the backend with **no CORS setup and no base URL**. Sign in with a
seeded account (see `database/incremental_dml.sql`).

Production build:

```powershell
npm run build        # outputs dist/
npm run preview      # serve the build locally
```

---

## 5. Public marketing site

```powershell
cd public-site
Copy-Item .env.example .env
notepad .env                           # set VITE_APP_URL=http://localhost:10000
npm install
npm run dev                            # → http://localhost:5174 (auto-next-port)
```

Every "Log in" button links to `VITE_APP_URL`. Build/preview identical to §4.

## 6. Validate the install

```powershell
# Backend — env/schema/import sanity + full pytest suite (166 tests)
python scripts\smoke_check.py
python scripts\run_tests.py

# Frontend SPA — component/unit suite (Vitest + Testing Library)
cd frontend; npm test; cd ..

# Public site — production build sanity
cd public-site; npm run build; cd ..
```

`start.ps1 -CheckOnly` prints a full PASS/FAIL snapshot (prereqs, deps, env
file — `backend/.env` or root `.env`, schema files, entry points, scripts).

---

## 7. Running all three together (dev cheat-sheet)

Three terminals from the repo root:

```powershell
# Terminal 1 — API on :10000 (hot reload)
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --port 10000 --reload --reload-dir backend

# Terminal 2 — App SPA on :5173 (proxies /api → :10000)
cd frontend; npm run dev

# Terminal 3 — Marketing site on :5174
cd public-site; npm run dev
```

Then open **http://localhost:5173** (app) and **http://localhost:5174** (site).

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Backend exits: *Missing required environment variable: DATABASE_URL* | No env file found. Create `backend/.env` (§3b) or root `.env`. |
| SPA loads but every API call 401/CORS-errors | Backend not running on :10000, or you built the SPA with a wrong `VITE_API_BASE_URL`. For dev keep it empty and use `npm run dev` (proxy). |
| Login works but session dies on refresh | Cookie issuance is opt-in (`AUTH_COOKIE=1`); the SPA uses Bearer tokens in localStorage — make sure you signed in through the app, not a stale cookie. |
| LAN phone can't stay logged in over plain HTTP | Set `COOKIE_SECURE=0` in `backend/.env` (only for trusted LAN testing). |
| WhatsApp sends silently no-op | Expected without credentials. Set `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_PHONE_ID`; also set `WHATSAPP_APP_SECRET` so webhook signature checks (B‑2) enforce. |
| Billing/emails do nothing | Optional integrations degrade gracefully — set the Razorpay / Resend vars to enable. |
| Port 10000/5173 already in use | Pass `-Port` to start.ps1; Vite auto-increments to 5174+. |
| New columns/tables missing at runtime | You skipped §2's incremental DDL — re-run `database/incremental_ddl.sql`. |

---

## 9. Deployment notes (summary)

- **API** → Render Web Service (`backend.app.main:app`, env vars from dashboard).
- **App SPA** → Render Static Site (`frontend/dist`, `VITE_API_BASE_URL=https://api.vahankhata.in`).
- **Marketing site** → Render Static Site (`public-site/dist`, `VITE_APP_URL=https://app.vahankhata.in`).
- Scheduled housekeeping → `.github/workflows/cron.yml` daily (secret `DATABASE_URL`) or a Render Cron Job running `python scripts/cron_daily.py`.

---

