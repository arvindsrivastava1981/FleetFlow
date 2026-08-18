"""VahanKhata application package.

Modular decomposition into cohesive packages.

Package map
-----------
api      : FastAPI router definitions + endpoint wiring (JSON API only)
core     : App config, security helpers (auth, escaping, rate-limit)
db       : Connection/factory helpers and typed row access
models   : Thin data access / domain query functions
schemas  : Pydantic v2 request/response contracts
schemas/constants
services : Business rules engine + WhatsApp/OCR/PDF/audit integrations
middleware : CSRF, auth dependency wiring

There is no server-rendered HTML layer. All UI lives in the React SPA
(`frontend/dist`, served by `main.py`); the backend returns JSON only.
"""