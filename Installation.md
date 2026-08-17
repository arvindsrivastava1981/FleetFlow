---

# 📦 Installation & Quickstart

> **FleetFlow** is a FastAPI (Python 3.12) app backed by PostgreSQL (Neon DB). No ORM, no
> Alembic — the schema is applied manually from `database/schema.sql`. Config is
> **env-driven and fail-fast**: the app refuses to boot without required variables.

---

## 1. Prerequisites

* **Python 3.12+** (target version, see `pyproject.toml`) with `pip`.
* A managed **PostgreSQL** instance (Neon DB) and its connection string.
* *(Optional)* a virtual environment — recommended:

```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

---

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Configure the environment

Copy the shape of `.env` (it is git-ignored) and fill in real values:

```bash
# .env  — shown for illustration; do not commit secrets
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/neondb?sslmode=require
USER_PASSWORD=change-me       # required in production (see below)
ENV=development                # omit/set "development" locally, "production" in deploy
```

### Required variables (the app fails fast if absent)

| Variable         | Required | Purpose                                                        |
| ---------------- | -------- | -------------------------------------------------------------- |
| `DATABASE_URL`   | Always   | Neon PostgreSQL connection string. Boot fails without it.      |
| `_PASSWORD` | In prod  |  login password. In production, `123` is **refused** — you must set an explicit strong value. |

Optional: `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_ID`, `WEBHOOK_VERIFY_TOKEN` (Phase C WhatsApp Cloud API — not used by the core demo).

---

## 4. Apply the database schema

FleetFlow **never runs DDL**. Apply it manually to your Neon instance:

```bash
psql "$DATABASE_URL" -f database/schema.sql
```

Also apply `database/incremental.sql` if you already have an older schema:

```bash
psql "$DATABASE_URL" -f database/incremental.sql
```

---

## 5. Run the app

### Entry point (modular FastAPI app)

This is the only entry point (`backend/app/main.py`) — see `Dockerfile` / `render.yaml`:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}
```

Open **http://localhost:10000** (or `$PORT` if set) — you'll be redirected to `/login`; use the `_PASSWORD` you set.

> The legacy single-file prototype (`fleetflow_interactive_demo.py` + `utils.py`) has been
> fully migrated into `backend/app/` and removed from the repo (see `PROJECT_STRUCTURE.md` §4).

---

## 6. Validate the install

Environment/schema/import sanity + full test suite (22 tests: rules-engine + route-security):

```bash
python scripts/smoke_check.py   # verifies env vars, rules band, package imports
python scripts/run_tests.py     # runs the full pytest suite (default: "tests")
```

---

## 7. Deployment (Render / Docker)

The `Dockerfile` runs the modular entry point with `--port ${PORT:-10000}` and exposes 10000.
See `render.yaml` for the web service: it sets `ENV=production`, injects `PORT`, and expects
`DATABASE_URL` + `_PASSWORD` provided as manual secrets in the Render dashboard
(`sync: false`). The `/healthz` route verifies the app boots **and** the DB is reachable.
