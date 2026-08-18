"""Razorpay billing client.

Uses Payment Links for everything — monthly, yearly, and vehicle-slot purchases.
No pre-created Plans needed. Recurring is handled by sending a new payment link
when `next_billing_date` approaches (the billing upgrade page shows a link).

Hardcoded pricing:
  Monthly  — ₹ 799 / month   (1 vehicle)
  Yearly   — ₹ 7,191 / year   (25% off: 799×12=9,588 × 0.75)
  Per-vehicle slot — ₹ 799   (one-time, raises fleet vehicle_limit by 1)
"""
from __future__ import annotations

import httpx

from backend.app.core.config import settings

_BASE_URL = "https://api.razorpay.com/v1"
_AUTH = (settings.razorpay_key_id or "", settings.razorpay_key_secret or "")

# ── hardcoded plan pricing ─────────────────────────────────────────────
MONTHLY_PRICE = 799.00
YEARLY_PRICE = 7191.00   # 25 % off: 799 × 12 × 0.75
VEHICLE_SLOT_PRICE = 799.00
# ────────────────────────────────────────────────────────────────────────


def _headers() -> dict:
    return {"Content-Type": "application/json"}


def _post(path: str, body: dict) -> dict:
    """POST to the Razorpay API; raises on HTTP errors."""
    if not settings.razorpay_key_id:
        raise RuntimeError("RAZORPAY_API_KEY is not configured in .env")
    resp = httpx.post(
        f"{_BASE_URL}{path}",
        json=body,
        auth=_AUTH,
        headers=_headers(),
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()


def _amount_paise(amount: float) -> int:
    """Convert INR float to paise (e.g. 799.00 → 79900)."""
    return int(round(amount * 100))


# ── customers ───────────────────────────────────────────────────────────

def create_customer(name: str, phone: str, email: str | None = None) -> dict:
    """Create a Razorpay customer to be mapped with fleet for billing."""
    return _post(
        "/customers",
        {
            "name": name,
            "contact": phone,
            "email": email or "",
            "fail_existing": "0",
        },
    )


# ── payment links (monthly / yearly / vehicle slot) ─────────────────────

def create_payment_link(
    amount: float,
    customer: dict | None,
    description: str,
    reference_id: str = "",
) -> dict:
    """Create a one-time payment link (works without Plans).

    *amount* is in ₹ (converted to paise).
    *customer* dict should have 'name','contact','email' if known.
    """
    link_body: dict = {
        "amount": _amount_paise(amount),
        "currency": "INR",
        "description": description,
        "accept_partial": False,
    }
    if customer:
        link_body["customer"] = {
            "name": customer.get("name", ""),
            "contact": customer.get("contact", customer.get("phone", "")),
            "email": customer.get("email", ""),
        }
    if reference_id:
        link_body["reference_id"] = reference_id
    return _post("/payment_links", link_body)

