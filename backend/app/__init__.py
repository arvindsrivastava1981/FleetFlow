"""FleetFlow application package.

Modular decomposition of the former single-file prototype
(`fleetflow_interactive_demo.py`) into cohesive packages.

Package map
-----------
api      : FastAPI router definitions + endpoint wiring
core     : App config, security helpers (auth, escaping, rate-limit)
db       : Connection/factory helpers and typed row access
models   : Thin data access / domain query functions
schemas  : Pydantic v2 request/response contracts
schemas/constants
services : Business rules engine + WhatsApp/OCR/PDF/audit integrations
web/templates : Server-rendered HTML chrome + page builders
web/static    : Tailwind-CDN app shells and JS for CDN-based UI
middleware : CSRF, auth dependency wiring
"""