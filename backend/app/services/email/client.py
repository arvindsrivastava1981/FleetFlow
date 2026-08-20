import os
import logging
import threading
from typing import Any, Optional
import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Template engine setup
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

def _is_email_configured() -> bool:
    return bool(settings.resend_api_key and settings.sender_email)

async def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    from_email: Optional[str] = None,
    attachments: Optional[list[dict[str, Any]]] = None,
) -> dict:
    """Send an email via the Resend HTTP API."""
    result = {"status": "skipped", "error": None}

    if not _is_email_configured():
        result["error"] = "email_not_configured"
        logger.warning("[email] Delivery skipped | RESEND_API_KEY or SENDER_EMAIL missing")
        return result

    try:
        api_key = settings.resend_api_key
        sender = from_email or settings.sender_email
        payload: dict[str, Any] = {
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "text": body,
        }
        if html_body:
            payload["html"] = html_body
        if attachments:
            payload["attachments"] = attachments

        logger.info("[email] Dispatching email via Resend | recipient=%s subject=%s", to_email, subject)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            response.raise_for_status()

        result["status"] = "sent"
        logger.info("[email] Email sent successfully | recipient=%s", to_email)
        return result

    except httpx.HTTPError as exc:
        result["status"] = "error"
        result["error"] = str(exc)
        logger.error("[email] Resend delivery failed | recipient=%s error=%s", to_email, exc)
        return result

async def send_manager_onboarding_email(
    to_email: str,
    manager_name: str,
    username: str,
    temporary_password: str,
    login_url: str,
    fleet_name: str,
    subscription_plan: str,
    subscription_expiry: str,
    vehicle_limit: int,
    driver_limit: int,
    default_batta_rate: float = 2500.00,
) -> dict:
    """Render and dispatch the Trip Manager onboarding welcome email."""
    template = env.get_template("manager_welcome.html")
    context = {
        "manager_name": manager_name,
        "username": username,
        "password": temporary_password,
        "login_url": login_url,
        "fleet_name": fleet_name,
        "subscription_plan": subscription_plan,
        "subscription_expiry": subscription_expiry,
        "vehicle_limit": vehicle_limit,
        "driver_limit": driver_limit,
        "default_batta_rate": f"{default_batta_rate:,.2f}",
        "support_email": settings.support_email,
    }
    
    html_content = template.render(context)
    plain_text = (
        f"Welcome to VahanKhata, {manager_name}!\n\n"
        f"You have been added as a Trip Manager for {fleet_name}.\n\n"
        f"LOGIN DETAILS:\n"
        f"URL: {login_url}\n"
        f"Username: {username}\n"
        f"Temporary Password: {temporary_password}\n\n"
        f"SUBSCRIPTION & FLEET LIMITS:\n"
        f"Plan: {subscription_plan} (Expires: {subscription_expiry})\n"
        f"Vehicle Limit: {vehicle_limit} trucks\n"
        f"Driver Limit: {driver_limit} drivers\n"
        f"Default Driver Batta: Rs. {default_batta_rate:,.2f} per trip\n\n"
        f"NEXT STEPS:\n"
        f"1. Login to {login_url}\n"
        f"2. Add your fleet vehicles\n"
        f"3. Add your drivers and configure WhatsApp numbers\n"
        f"4. Create your first active trip with cash advance.\n"
    )
    
    return await send_email(
        to_email=to_email,
        subject=f"Welcome to VahanKhata - Manager Credentials for {fleet_name}",
        body=plain_text,
        html_body=html_content,
    )


# ---------------------------------------------------------------------------#
# Plug-and-play wiring helpers
# ---------------------------------------------------------------------------#
def manager_onboarding_email_context(
    manager_full_name: str,
    manager_username: str,
    temporary_password: str,
    fleet: dict,
    login_url: str,
) -> dict:
    """Build the data dict for `send_manager_onboarding_email` from a fleet row.

    Derives the fleet display name and subscription critique fields that the
    existing email signature expects. `fleet` is a `fleets` row enriched with
    `plan_name` (see `fleets.get_fleet_email_context`).

    If `temporary_password` is falsy the email *will not be dispatched* by the
    caller — it is up to the caller to only build/send on the create path.
    """
    from backend.app.services.audit.cash import DEFAULT_DRIVER_BATTA as _default_batta

    plan_name = (fleet.get("plan_name") or "Trial").strip()
    return {
        "to_email": fleet.get("email") or "",
        "manager_name": manager_full_name,
        "username": manager_username,
        "temporary_password": temporary_password,
        "login_url": login_url,
        "fleet_name": (fleet.get("owner_name") or "your fleet").strip(),
        "subscription_plan": plan_name,
        "subscription_expiry": _mail_subscription_expiry(fleet),
        "vehicle_limit": int(fleet.get("vehicle_limit") or 1),
        "driver_limit": int(fleet.get("driver_limit") or 0),
        "default_batta_rate": float(fleet.get("default_batta_rate") or _default_batta or 2500.00),
    }


def _mail_subscription_expiry(fleet: dict) -> str:
    """Pick the most meaningful 'valid until' date for the welcome email."""
    from datetime import datetime, date as _date

    trial_ends = fleet.get("trial_ends_at")
    billing_date = fleet.get("next_billing_date")
    candidates = [c for c in (trial_ends, billing_date) if c]
    if not candidates:
        return "your subscription end date"
    # Trial-end takes precedence for TRIAL fleets; otherwise the next billing date.
    chosen = trial_ends if fleet.get("subscription_status") == "TRIAL" and trial_ends else billing_date
    if not chosen:
        chosen = candidates[0]
    if isinstance(chosen, (datetime, _date)):
        return chosen.isoformat()
    return str(chosen)


def dispatch_sync(
    fn,
    **kwargs: Any,
) -> dict:
    """Run an async email function in a background thread (fire-and-forget).

    The low-level `send_email` already short-circuits (`status: skipped`) when
    Resend is not configured, and all failures are caught and logged before
    this wrapper returns, so **no caller exception can propagate**. Used from
    sync (legacy HTML) routes and from event loops without blocking them.
    """
    result: dict = {"status": "skipped", "error": None, "queued": False}
    import asyncio as _asyncio

    def _misfire(method):
        target = getattr(_asyncio, method)
        try:
            target(fn(**kwargs))
        except Exception as exc:  # noqa: BLE001
            logger.error("[email] async wrapper misfire | fn=%s error=%s", getattr(fn, "__name__", fn), exc)

    try:
        loop = _asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    try:
        if loop is not None and loop.is_running():
            # We're on a live event loop; schedule on it without awaiting.
            _misfire("create_task")
            result["queued"] = True
            return result
        thread = threading.Thread(target=_misfire, kwargs={"method": "run"}, daemon=True)
        thread.start()
        result["queued"] = True
        return result
    except Exception as exc:  # noqa: BLE001
        logger.error("[email] dispatch_sync failed | error=%s", exc)
        return result


def send_manager_onboarding_email_sync(
    to_email: str,
    manager_name: str,
    username: str,
    temporary_password: str,
    login_url: str,
    fleet_name: str,
    subscription_plan: str,
    subscription_expiry: str,
    vehicle_limit: int,
    driver_limit: int,
    default_batta_rate: float = 2500.00,
) -> dict:
    """Fire-and-forget wrapper around the async manager onboarding email.

    Identical signature to `send_manager_onboarding_email` but safe to call
    from a synchronous route. Returns immediately; failures never raise.
    """
    if not temporary_password:
        return {"status": "skipped", "error": "no_temporary_password", "queued": False}
    if not to_email:
        return {"status": "skipped", "error": "no_recipient_email", "queued": False}
    return dispatch_sync(
        send_manager_onboarding_email,
        to_email=to_email,
        manager_name=manager_name,
        username=username,
        temporary_password=temporary_password,
        login_url=login_url,
        fleet_name=fleet_name,
        subscription_plan=subscription_plan,
        subscription_expiry=subscription_expiry,
        vehicle_limit=vehicle_limit,
        driver_limit=driver_limit,
        default_batta_rate=default_batta_rate,
    )