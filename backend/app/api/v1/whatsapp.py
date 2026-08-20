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

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from backend.app.core.config import settings
from backend.app.db.connection import get_db
from backend.app.db.queries.trips import (  # noqa: PLC2701 (webhook owns driver consent)
    driver_consent as record_driver_consent,
    get_active_trip_for_driver,
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

router = APIRouter(prefix="/api/v1/whatsapp")

# ---------------------------------------------------------------------------#


def _configured() -> bool:
    """True when the runtime has the Meta Cloud credentials wired."""
    return bool(settings.whatsapp_access_token and settings.whatsapp_phone_id)


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
    try:
        payload = await request.json()
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
async def whatsapp_send(body: dict | None = None) -> JSONResponse:
    """Send an outbound template message (idempotent, best-effort).

    Without a configured ``WHATSAPP_ACCESS_TOKEN`` this is a documented no-op so
    the callers (manager approvals / driver confirmations) can fire-and-forget.
    Replace the body with a live Meta Graph call when credentials are present.
    """
    _ = body or {}
    if not _configured():
        return JSONResponse(content={"sent": False, "reason": "unconfigured"}, status_code=200)
    # TODO(Phase C): POST to https://graph.facebook.com/v20.0/{phone_id}/messages
    # with an approved template; today this is a stub to keep the contract stable.
    return JSONResponse(content={"sent": False, "reason": "not_wired"}, status_code=200)


__all__ = ["router", "ROLE_DRIVER", "ROLE_MANAGER"]