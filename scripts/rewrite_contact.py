"""One-off: rewrite contact.py with correct indentation."""
import pathlib

path = pathlib.Path(
    r"c:\Personal\projects\FleetFlow\backend\app\api\v1\contact.py"
)

content = '''"""Public contact-form endpoint — no authentication required.

Receives a visitor's message from the marketing site Contact page and emails
it to the support inbox (default ``support@vahankhata.in``) via Resend.
Protected by a honeypot field and a simple per-IP rate limiter.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request

from backend.app.api.v1.deps import _ok
from backend.app.schemas.api_v1 import ContactRequest, ContactResponse, Data
from backend.app.services.email.client import send_contact_notification

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)

# --- In-memory rate limiter (single-process) --------------------------------
# Caps submissions per IP to keep the public endpoint abuse-resistant.
# On multi-worker deploys this is per-worker; the honeypot field is the
# primary bot defence and remains effective regardless.
_rate_bucket: dict[str, list[float]] = defaultdict(list)
_RATE_WINDOW_S = 60   # seconds
_RATE_CAP = 5         # max submissions per IP per window


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(ip: str) -> bool:
    """Return True if *ip* has exceeded the submission cap (and record the hit)."""
    now = time.monotonic()
    window = now - _RATE_WINDOW_S
    recent = [t for t in _rate_bucket[ip] if t > window]
    if len(recent) >= _RATE_CAP:
        _rate_bucket[ip] = recent
        return True
    recent.append(now)
    _rate_bucket[ip] = recent
    return False


@router.post("/contact", response_model=Data[ContactResponse])
async def api_contact(request: Request, payload: ContactRequest):
    """Accept a contact-form message and email it to support.

    Public (unauthenticated) endpoint. Rate-limited per IP and protected by a
    hidden honeypot field (``website``) to deter bots.
    """
    ip = _client_ip(request)

    # --- Honeypot -----------------------------------------------------------
    # Bots that auto-fill every field trip this trap. Silently succeed so the
    # bot gets no signal that it was detected.
    if payload.website:
        logger.info("[contact] honeypot triggered | ip=%s", ip)
        return _ok({"sent": True, "message": "Your message has been sent. We'll reply within one business day."})

    # --- Rate limit ---------------------------------------------------------
    if _rate_limited(ip):
        logger.warning("[contact] rate limit exceeded | ip=%s", ip)
        raise HTTPException(
            status_code=429,
            detail="Too many submissions. Please wait a minute and try again.",
        )

    # --- Send ---------------------------------------------------------------
    result = await send_contact_notification(
        name=payload.name,
        sender_email=payload.email,
        message=payload.message,
        firm=payload.firm,
        phone=payload.phone,
    )

    status = result.get("status")
    if status == "sent":
        logger.info(
            "[contact] message delivered to support | ip=%s from=%s",
            ip, payload.email,
        )
        return _ok({"sent": True, "message": "Your message has been sent. We'll reply within one business day."})

    # Email transport not configured (e.g. local dev / CI without Resend keys).
    if status == "skipped" and result.get("error") == "email_not_configured":
        logger.warning(
            "[contact] email transport not configured; message not delivered | ip=%s",
            ip,
        )
        return _ok({
            "sent": False,
            "message": "Your message was received. (Email delivery is not configured in this environment.)",
        })

    # Real delivery failure — surface a service-unavailable so the caller knows.
    logger.error(
        "[contact] delivery failed | ip=%s status=%s error=%s",
        ip, status, result.get("error"),
    )
    raise HTTPException(
        status_code=503,
        detail="We could not send your message right now. Please try again later or email support directly.",
    )
'''

path.write_text(content, encoding="utf-8")
print("Rewrote contact.py —", len(content), "bytes")
