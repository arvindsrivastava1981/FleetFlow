"""Phase C single WhatsApp webhook — verification + role routing.

These tests cover the single-bot contract without credentials or a live Meta
Graph API: the GET verification handshake, the pure routing helpers in
``services/whatsapp``, and the POST webhook's dependency on ``get_user_by_phone``
for sender-role resolution.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.api.v1 import whatsapp as whatsapp_router
from backend.app.main import app
from backend.app.services import whatsapp as wa


def test_normalise_number_adds_country_code() -> None:
    """Meta's bare WA_ID ``919873456789`` maps to the stored ``+919873456789``."""
    assert wa.normalise_number("919873456789") == "+919873456789"


def test_normalise_number_strips_plus_and_blank() -> None:
    """A ``+``-prefixed or empty WA_ID still resolves to a canonical form."""
    assert wa.normalise_number("+919873456789") == "+919873456789"
    assert wa.normalise_number("") == ""
    assert wa.normalise_number("   ") == ""


def test_classify_sender_by_role() -> None:
    """One bot number, two dialects: drivers intake, managers approve."""
    assert wa.classify_sender("driver") == wa.ROLE_DRIVER
    assert wa.classify_sender("trip_manager") == wa.ROLE_MANAGER
    assert wa.classify_sender("super_admin") == wa.ROLE_MANAGER
    assert wa.classify_sender("unknown") is None
    assert wa.classify_sender(None) is None


def test_extract_text_and_wa_id_from_delivery() -> None:
    """The Meta delivery shape yields the sender number + free text body."""
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "text": {"body": "Diesel 2000"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    assert wa.extract_wa_id(payload) == "919876543210"
    assert wa.extract_text(payload) == "Diesel 2000"
    # Empty / non-message payloads degrade to safe values.
    assert wa.extract_wa_id({}) == ""
    assert wa.extract_text({}) == ""


def test_webhook_verify_handshake(monkeypatch) -> None:
    """The single Meta handshake echoes the challenge when the token matches."""
    # The router reads `settings.webhook_verify_token` (core.config singleton).
    monkeypatch.setattr(whatsapp_router.settings, "webhook_verify_token", "vk_verify_2024")
    client = TestClient(app)

    ok = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub_mode": "subscribe", "hub_challenge": "1234", "hub_verify_token": "vk_verify_2024"},
    )
    assert ok.status_code == 200
    assert ok.text == "1234"

    bad = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub_mode": "subscribe", "hub_challenge": "1234", "hub_verify_token": "nope"},
    )
    assert bad.status_code == 403
    assert bad.text == "forbidden"


def test_webhook_post_acknowledges_unknown_delivery() -> None:
    """An inbound delivery with no resolvable number returns OK (never fails)."""
    client = TestClient(app)
    resp = client.post("/api/v1/whatsapp/webhook", json={})
    assert resp.status_code == 200
    assert resp.json() == "ok"
