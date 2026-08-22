"""Outbound WhatsApp Cloud API sender (Phase C / feature F-1).

Thin, failure-isolating wrapper around the Meta Graph API. When credentials
are not configured every call degrades to ``{"sent": False, ...}`` so callers
(escalation notifications, manager confirmations) can fire-and-forget exactly
like the pre-Phase-C stub — production simply flips the env vars on.
"""
from __future__ import annotations

import logging

import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

_GRAPH_MESSAGES_URL = "https://graph.facebook.com/v20.0/{phone_id}/messages"


def configured() -> bool:
    """True when WHATSAPP_ACCESS_TOKEN + WHATSAPP_PHONE_ID are both set."""
    return bool(settings.whatsapp_access_token and settings.whatsapp_phone_id)


def send_text(to_phone: str, body: str) -> dict:
    """Send a plain text message to *to_phone* (E.164, e.g. +9198...).

    Never raises: transport/API failures are logged and returned as
    ``{"sent": False, "reason": ...}`` so notification paths stay best-effort.
    """
    if not configured():
        return {"sent": False, "reason": "unconfigured"}
    try:
        resp = httpx.post(
            _GRAPH_MESSAGES_URL.format(phone_id=settings.whatsapp_phone_id),
            json={
                "messaging_product": "whatsapp",
                "to": to_phone,
                "type": "text",
                "text": {"preview_url": False, "body": body},
            },
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            timeout=10,
        )
        if resp.status_code >= 400:
            logger.warning(
                "WhatsApp send to %s failed (%s): %s",
                to_phone, resp.status_code, resp.text[:200],
            )
            return {"sent": False, "status": resp.status_code}
        return {"sent": True, "status": resp.status_code}
    except Exception as exc:  # noqa: BLE001 - notifications never break flows
        logger.warning("WhatsApp send to %s errored: %s", to_phone, exc)
        return {"sent": False, "reason": str(exc)[:120]}
