"""Rules router — display anomaly rules explainer.

Provides GET /rule-engine for the admin-only rule explanation page.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.core.security import require_admin

router = APIRouter()


@router.get("/rule-engine")
def rule_engine_explainer(request: Request) -> dict:
    """Render the rule engine explainer page (admin-only).

    Returns a dict that the template can render, using static constants
    from the app config.
    """
    guard = require_admin(request)
    if guard is not None:
        return guard

    from backend.app.db.queries.rules import get_rule_definitions
    rules = get_rule_definitions()
    return {"rules": rules}