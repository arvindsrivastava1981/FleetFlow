"""Dump the FastAPI OpenAPI schema to docs/openapi.json (audit E-9).

Gives frontend/external consumers a machine-readable API contract. Regenerate
after any route/schema change:

    python scripts/export_openapi.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.main import app  # noqa: E402


def main() -> int:
    out = ROOT / "docs" / "openapi.json"
    schema = app.openapi()
    out.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(schema.get('paths', {}))} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
