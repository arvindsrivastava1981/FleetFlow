"""Single WhatsApp bot webhook — one entrypoint, routed by sender role (Phase C).

Drivers and managers talk to the SAME bot phone number. This router owns the
webhook (Meta Cloud API) and routes each inbound delivery to the sender's
existing role-scoped flow:

- OAUTH verification:  Meta GETs the endpoint on setup (hub.challenge handshake).
- Inbound messages:    Meta POSTs deliveries; the sender number is resolved to a
  ``users`` row, then the message is routed to the driver expense-intake flow
  (``POST /api/v1/expenses``) or the manager escalation-approval flow
  (``POST /api/v1/expenses/{id}/action``). The role-aware JSON endpoints above are
  the in-app transport; this webhook is the same logic over WhatsApp.

Nothing here requires credentials at import time: until the app is configured with
``WHATSAPP_ACCESS_TOKEN`` / ``WHATSAPP_PHONE_ID`` / ``WEBHOOK_VERIFY_TOKEN``, the
endpoints verify as best-effort and acknowledge deliveries with a 200 (Meta
retries/blacklists webhooks that do not return promptly), leaving the in-app
simulators untouched.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from backend.app.api.v1.deps import _trip_forbidden
from backend.app.core.config import settings
from backend.app.core.security import require_json_role
from backend.app.db.connection import get_db
from backend.app.db.queries.expenses import (
    action_expense_status,
    get_expense_by_id,
    get_expense_trip_code,
)
from backend.app.db.queries.trips import (  # noqa: PLC2701 (webhook owns driver consent)
    driver_consent as record_driver_consent,
)
from backend.app.db.queries.trips import (
    get_active_trip_for_driver,
    get_trip_by_code,
)
from backend.app.db.queries.users import get_user_by_phone
from backend.app.services.whatsapp import (
    ROLE_DRIVER,
    ROLE_MANAGER,
    classify_sender,
    extract_text,
    extract_wa_id,
    normalise_number,
)
from backend.app.services.whatsapp.send import send_text

router = APIRouter(prefix="/api/v1/whatsapp")

# ---------------------------------------------------------------------------#


def _configured() -> bool:
    """True when the runtime has the Meta Cloud credentials wired."""
    return bool(settings.whatsapp_access_token and settings.whatsapp_phone_id)


def _signature_valid(raw: bytes, header: str | None) -> bool:
    """Verify Meta's ``X-Hub-Signature-256`` ("sha256=<hex>" HMAC of raw body).

    Enforcement activates only once ``WHATSAPP_APP_SECRET`` is configured
    (audit B-2): unconfigured dev/test environments keep accepting unsigned
    payloads so local simulators and the test-suite stay friction-free.
    """
    secret = settings.whatsapp_app_secret
    if not secret:
        return True
    if not header or not header.lower().startswith("sha256="):
        return False
    digest = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, header.split("=", 1)[1].strip().lower())


# "APPROVE 42" / "REJECT #42" / "Approved 42" — manager chat-approval syntax.
_MANAGER_ACTION_RE = re.compile(
    r"^(APPROV(?:E|ED)|REJECT(?:ED)?)\s+#?(\d{1,9})$", re.IGNORECASE
)


def _parse_manager_action(text: str):
    """Parse an approval command → ``(action, expense_id)`` or ``None``.

    Accepts APPROVE/APPROVED/REJECT/REJECTED (case-insensitive, optional '#')
    followed by the numeric expense id, e.g. ``"approve 128"``.
    """
    match = _MANAGER_ACTION_RE.match((text or "").strip().upper())
    if not match:
        return None
    action = "APPROVE" if match.group(1).startswith("APPROV") else "REJECT"
    return action, int(match.group(2))


@router.get("/webhook")
def whatsapp_webhook_verify(
    hub_mode: str | None = None,
    hub_challenge: str | None = None,
    hub_verify_token: str | None = None,
) -> PlainTextResponse:
    """Meta platform setup: reply with ``hub.challenge`` when the token matches."""
    expected = settings.webhook_verify_token or ""
    if (
        hub_mode == "subscribe"
        and hub_challenge
        and expected
        and hub_verify_token == expected
    ):
        return PlainTextResponse(hub_challenge, status_code=200)
    return PlainTextResponse("forbidden", status_code=403)


@router.post("/webhook")
async def whatsapp_webhook(request: Request) -> JSONResponse:
    """Single inbound entrypoint for ALL bot messages (driver + manager).

    Resolves the sender's number to a user (by normalized ``+91`` phone), maps
    their role to a routing dialect, and either fires the driver/manager flow or
    acknowledges-and-drops unknown/unsupported senders. Always returns a quick 200
    so Meta does not retry undeliverable events.
    """
    # Audit B-2: verify Meta's X-Hub-Signature-256 BEFORE parsing/routing.
    # See _signature_valid: enforcement is active whenever WHATSAPP_APP_SECRET
    # is configured (i.e., every production deployment).
    raw = await request.body()
    if not _signature_valid(raw, request.headers.get("x-hub-signature-256")):
        logging.getLogger(__name__).warning(
            "WhatsApp webhook rejected: missing/invalid X-Hub-Signature-256"
        )
        return JSONResponse(content={"error": "invalid signature"}, status_code=401)
    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001 - malformed body
        return JSONResponse(content="ok", status_code=200)

    wa_id = extract_wa_id(payload)
    if not wa_id:
        # Meta status/echoes (no inbound message) are acknowledged, not routed.
        return JSONResponse(content="ok", status_code=200)

    phone = normalise_number(wa_id)
    with get_db() as conn:
        user = get_user_by_phone(conn, phone)

    dialect = classify_sender((user or {}).get("role") if user else None)
    if dialect is None:
        # Unbound number (no registered user) or a role we do not extend on
        # WhatsApp: acknowledge-and-drop; the webhook is not a message sink.
        return JSONResponse(content="ok", status_code=200)

    text = extract_text(payload)
    # Route: driver consent (Option 1) — a driver explicitly accepts the
    # settlement of their current trip by sending a consent keyword. The
    # webhook resolves the sender (authenticated by their WhatsApp number),
    # so the recorded identity is server-authoritative.
    if dialect == ROLE_DRIVER and user:
        consent_keywords = {"CONSENT", "CONFIRM", "ACCEPT", "स्वीकृत", "हाँ"}
        if text.strip().upper() in consent_keywords or any(
            kw in text.strip().upper() for kw in consent_keywords
        ):
            with get_db() as conn:
                trip = get_active_trip_for_driver(conn, user["user_id"])
                if trip:
                    written = record_driver_consent(
                        conn, trip["trip_code"], user["user_id"]
                    )
                    return JSONResponse(
                        content={
                            "received": True,
                            "routed_to": ROLE_DRIVER,
                            "consented": written,
                            "trip_code": trip["trip_code"],
                            "wa_id": wa_id,
                        },
                        status_code=200,
                    )
                return JSONResponse(
                    content={
                        "received": True,
                        "routed_to": ROLE_DRIVER,
                        "consented": False,
                        "reason": "no_active_trip",
                        "wa_id": wa_id,
                    },
                    status_code=200,
                )
    # ── F-1: manager chat-approvals ("APPROVE 42" / "REJECT 42") ───────────
    # Mirrors POST /api/v1/expenses/{id}/action's authorization (role +
    # trip-ownership via _trip_forbidden) without duplicating its HTTP layer.
    if dialect == ROLE_MANAGER and user:
        parsed = _parse_manager_action(text)
        if parsed:
            action, expense_id = parsed
            status = "APPROVED" if action == "APPROVE" else "REJECTED"
            with get_db() as conn:
                expense_code = get_expense_trip_code(conn, expense_id)
                if not expense_code:
                    return JSONResponse(content={
                        "received": True, "routed_to": ROLE_MANAGER,
                        "applied": False, "reason": "expense_not_found",
                    }, status_code=200)
                trip = get_trip_by_code(conn, expense_code)
                if trip is None or _trip_forbidden(conn, user, trip):
                    return JSONResponse(content={
                        "received": True, "routed_to": ROLE_MANAGER,
                        "applied": False, "reason": "forbidden",
                    }, status_code=200)
                row = get_expense_by_id(conn, expense_id)
                if (
                    status == "APPROVED"
                    and row is not None
                    and row.get("exp_type") == "SETTLEMENT_TRANSFER"
                ):
                    # Settlement acceptances carry a ledger-recheck in the app;
                    # keep those on the authenticated surface for safety.
                    return JSONResponse(content={
                        "received": True, "routed_to": ROLE_MANAGER,
                        "applied": False,
                        "reason": "settlement_needs_app_confirmation",
                    }, status_code=200)
                action_expense_status(conn, expense_id, status)
                driver_phone = None
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT phone FROM users WHERE id = %s",
                        (trip.get("driver_user_id"),),
                    )
                    driver_phone = (cur.fetchone() or {}).get("phone")
                except Exception:  # noqa: BLE001 - notification lookup only
                    driver_phone = None
            label = "✅ Approved" if status == "APPROVED" else "❌ Deducted"
            if driver_phone:
                send_text(
                    driver_phone,
                    f"{label} · Trip {expense_code} · expense #{expense_id}",
                )
            return JSONResponse(content={
                "received": True, "routed_to": ROLE_MANAGER,
                "applied": True, "action": action,
                "expense_id": expense_id, "trip_code": expense_code,
            }, status_code=200)

    # Surface the routing decision so operational logs/deploys can follow a
    # single message through the single-bot pipeline. The actual intake/approval
    # side-effects live in the role-scoped endpoints (expenses.py).
    return JSONResponse(
        content={
            "received": True,
            "routed_to": dialect,
            "wa_id": wa_id,
            "has_text": bool(text),
        },
        status_code=200,
    )


@router.post("/send")
async def whatsapp_send(request: Request, body: dict | None = None) -> JSONResponse:
    """Send an outbound template message (idempotent, best-effort).

    Auth-gated (audit B-3): only an authenticated trip_manager/super_admin may
    trigger outbound sends, so Phase-C credentials can never be used as an
    open relay. Without a configured ``WHATSAPP_ACCESS_TOKEN`` this remains a
    documented no-op so callers can fire-and-forget.
    """
    guard = require_json_role(request, "trip_manager", "super_admin")
    if guard is not None:
        return guard
    payload = body or {}
    to = str(payload.get("to") or "").strip()
    text = str(payload.get("text") or "").strip()
    if not to or not text:
        return JSONResponse(
            content={"error": "to and text are required"}, status_code=400
        )
    # Phase C (F-1): live Graph-API send when configured; graceful no-op
    # payload otherwise (identical contract to the pre-Phase-C stub).
    return JSONResponse(content=send_text(to, text), status_code=200)
    # with an approved template; today this is a stub to keep the contract stable.
    return JSONResponse(content={"sent": False, "reason": "not_wired"}, status_code=200)


__all__ = ["router", "ROLE_DRIVER", "ROLE_MANAGER"]
