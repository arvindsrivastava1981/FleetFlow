---

# 📦 Installation & Quickstart

> **FleetFlow** is a FastAPI (Python 3.12) app backed by PostgreSQL (Neon DB). No ORM, no
> Alembic — the schema is applied manually from `database/schema.sql`. Config is
> **env-driven and fail-fast**: the app refuses to boot without required variables.

---



## 2. Backend Run

```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

uvicorn backend.app.main:app --host 0.0.0.0 --port 10000 --reload

Open **http://localhost:10000**
```

npm install
# front end
- cd c:\Personal\projects\FleetFlow\frontend

- `npm run dev` — start the Vite dev server (hot reload)

- `npm run build` — production build ✓ (works)

- `npm run preview` — serve the built `dist/` locally




npm run build

So depending on what you want:

__For local development:__

```powershell
npm run dev
```

__To serve the production build you just made:__

```powershell
npm run preview
```



## Validate the install

Environment/schema/import sanity + full test suite (22 tests: rules-engine + route-security):

```bash
python scripts/smoke_check.py   # verifies env vars, rules band, package imports
python scripts/run_tests.py     # runs the full pytest suite (default: "tests")
```

