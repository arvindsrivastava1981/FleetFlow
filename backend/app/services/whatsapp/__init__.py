"""WhatsApp Cloud API integration — the SINGLE-bot routing contract (Phase C, G1/G6/G9).

One bot phone number owns one webhook endpoint (``backend/app/api/v1/whatsapp.py``).
Every inbound delivery is resolved by the sender's WhatsApp number to a ``users``
row (see ``db/queries/users.py::get_user_by_phone``), and the payload is routed to
the existing role-scoped JSON flows that already back the in-app simulators:

- **driver**   -> expense intake (mirrors ``POST /api/v1/expenses``)
- **manager**  -> escalation approvals (mirrors ``POST /api/v1/expenses/{id}/action``)

The pure helpers here have no DB side-effects and no network I/O so they are
unit-testable without credentials or a live Meta Graph API.
"""

from __future__ import annotations

from typing import Any

# System invariant: all Indian numbers are stored/expected with the +91 prefix.
_COUNTRY_CODE = "+91"

# Role bucket names returned by ``classify_sender``. A trip_manager and
# super_admin both speak the manager dialect (escalation approvals); a driver
# speaks the receipt dialect.
ROLE_DRIVER = "driver"
ROLE_MANAGER = "manager"

_MANAGER_ROLES: frozenset[str] = frozenset({"trip_manager", "super_admin"})


def normalise_number(wa_id: str) -> str:
    """Normalize a WhatsApp ``WA_ID`` to the canonical (user-stored) form.

    Meta sends a bare digits ``wa_id`` (e.g. ``919873456789``) while the
    ``users.phone`` columns are stored with the ``+91`` country code. This adds
    the prefix (or strips a redundant ``+``) so a lookup by ``get_user_by_phone``
    matches, while leaving `none`/empty input as ``""``.
    """
    digits = (wa_id or "").strip().lstrip("+").strip()
    if not digits:
        return ""
    if not digits.startswith(_COUNTRY_CODE[1:]):  # "91" without the "+"
        digits = _COUNTRY_CODE[1:] + digits
    return _COUNTRY_CODE + digits


def classify_sender(role: str | None) -> str | None:
    """Map a resolved user role to the webhook routing dialect (or None).

    Returns ``ROLE_DRIVER`` for ``driver``, ``ROLE_MANAGER`` for
    ``trip_manager``/``super_admin``, and ``None`` for any other/unknown role so
    the webhook can acknowledge-and-drop unbound senders.
    """
    if role == "driver":
        return ROLE_DRIVER
    if role in _MANAGER_ROLES:
        return ROLE_MANAGER
    return None


def extract_text(payload: dict[str, Any]) -> str:
    """Pull the inbound free-text message from a Meta webhook delivery."""
    try:
        entries = payload.get("entry") or []
        for entry in entries:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                for message in value.get("messages") or []:
                    text = (message.get("text") or {}).get("body") or ""
                    if text:
                        return text
    except (AttributeError, TypeError):  # defensive: malformed / non-dict parts
        pass
    return ""


def extract_wa_id(payload: dict[str, Any]) -> str:
    """Pull the sender's WhatsApp ID (WA_ID) from a Meta webhook delivery."""
    try:
        entries = payload.get("entry") or []
        for entry in entries:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                for message in value.get("messages") or []:
                    wa_id = message.get("from") or message.get("wa_id") or ""
                    if wa_id:
                        return wa_id
    except (AttributeError, TypeError):
        pass
    return ""
