"""Tests for the public `POST /api/v1/contact` endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1 import contact as contact_module
from backend.app.main import app
from backend.app.services.email import client as email_client

client = TestClient(app)

VALID_BODY = {
    "name": "Rajesh Kumar",
    "email": "rajesh@firm.com",
    "phone": "+91 9876543210",
    "firm": "Kumar Transport",
    "message": "I'd like to know more about your pricing.",
}


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the in-memory contact rate limiter between tests."""
    contact_module._rate_bucket.clear()
    yield
    contact_module._rate_bucket.clear()


def test_contact_valid_submission(monkeypatch):
    """A valid form posts to the support inbox and returns 200 with sent=True."""
    captured: dict = {}

    async def fake_send_email(**kwargs):
        captured.update(kwargs)
        return {"status": "sent", "error": None}

    monkeypatch.setattr(email_client, "send_email", fake_send_email)

    resp = client.post("/api/v1/contact", json=VALID_BODY)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["sent"] is True
    assert "has been sent" in body["data"]["message"]

    # Email routed to support with visitor's email as reply_to
    assert captured["to_email"] == "support@vahankhata.in"
    assert captured["reply_to"] == "rajesh@firm.com"
    assert "Rajesh" in captured["subject"]
    assert "pricing" in captured["body"]


def test_contact_honeypot_bot_silently_accepts(monkeypatch):
    """A filled honeypot means a bot — 200 OK but no email is sent."""

    async def fake_send_email(**kwargs):  # pragma: no cover - failure path
        pytest.fail("send_email must not be called when the honeypot is filled")

    monkeypatch.setattr(email_client, "send_email", fake_send_email)

    resp = client.post(
        "/api/v1/contact", json={**VALID_BODY, "website": "http://spam.example"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["sent"] is True
    assert "has been sent" in body["data"]["message"]


def test_contact_missing_required_fields_returns_422():
    """Pydantic rejects bodies missing name, email, or message."""
    resp = client.post("/api/v1/contact", json={"name": "Test"})
    assert resp.status_code == 422


def test_contact_invalid_email_returns_422():
    """The field_validator rejects malformed email addresses."""
    resp = client.post(
        "/api/v1/contact",
        json={"name": "Test", "email": "not-an-email", "message": "Hello"},
    )
    assert resp.status_code == 422


def test_contact_rate_limit_returns_429(monkeypatch):
    """The 6th submission from the same IP within the window is blocked."""

    async def fake_send_email(**kwargs):
        return {"status": "sent", "error": None}

    monkeypatch.setattr(email_client, "send_email", fake_send_email)

    for _ in range(5):
        resp = client.post("/api/v1/contact", json=VALID_BODY)
        assert resp.status_code == 200

    resp = client.post("/api/v1/contact", json=VALID_BODY)
    assert resp.status_code == 429
    assert "Too many" in resp.json()["error"]


def test_contact_email_not_configured(monkeypatch):
    """When Resend is not configured, the endpoint returns 200 with sent=False."""

    async def fake_send_email(**kwargs):
        return {"status": "skipped", "error": "email_not_configured"}

    monkeypatch.setattr(email_client, "send_email", fake_send_email)

    resp = client.post("/api/v1/contact", json=VALID_BODY)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["sent"] is False
    assert "not configured" in body["data"]["message"]


def test_contact_email_delivery_failure(monkeypatch):
    """A real Resend delivery failure surfaces as 503."""

    async def fake_send_email(**kwargs):
        return {"status": "error", "error": "resend_api_error"}

    monkeypatch.setattr(email_client, "send_email", fake_send_email)

    resp = client.post("/api/v1/contact", json=VALID_BODY)
    assert resp.status_code == 503
    assert "could not send" in resp.json()["error"].lower()
