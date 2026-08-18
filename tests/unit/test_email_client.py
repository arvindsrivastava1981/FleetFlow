"""Unit tests for the plug-and-play manager onboarding email service.

These verify the data plumbing (recipient override, correct fleet/subscription
derivation) and the template rendering without touching a live DB or Resend.
The low-level HTTP client (`send_email`) is patched out.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.app.services.email import client as email_client


@pytest.fixture
def fleet_row() -> dict:
    """A fleet row as returned by `get_fleet_email_context`."""
    return {
        "id": 7,
        "owner_name": "Arvind Srivastava",
        "email": "billing@arvind.example",
        "subscription_status": "ACTIVE",
        "vehicle_limit": 3,
        "driver_limit": 4,
        "trial_ends_at": None,
        "next_billing_date": date(2026, 9, 18),
        "plan_name": "Monthly \u20b9799 Plan",
        "default_batta_rate": None,
    }


def test_manager_onboarding_email_context_derives_fields(fleet_row):
    """The helper maps a fleet row onto every field the template needs."""
    ctx = email_client.manager_onboarding_email_context(
        manager_full_name="Ravi Kumar",
        manager_username="ravi",
        temporary_password="s3cret",
        fleet=fleet_row,
        login_url="https://app.vahankhata.com/login",
    )
    assert ctx["to_email"] == "billing@arvind.example"
    assert ctx["manager_name"] == "Ravi Kumar"
    assert ctx["username"] == "ravi"
    assert ctx["temporary_password"] == "s3cret"
    assert ctx["login_url"] == "https://app.vahankhata.com/login"
    assert ctx["fleet_name"] == "Arvind Srivastava"
    assert ctx["subscription_plan"] == "Monthly \u20b9799 Plan"
    assert ctx["vehicle_limit"] == 3
    assert ctx["driver_limit"] == 4
    # Subscription expiry picks next_billing_date (non-TRIAL fleet).
    assert ctx["subscription_expiry"] == "2026-09-18"
    # No default_batta_rate on the fleet -> product default used.
    assert ctx["default_batta_rate"] == 2500.00


def test_manager_onboarding_email_context_trial_uses_trial_end(fleet_row):
    """A TRIAL fleet advertises the trial-end as its validity date."""
    row = {**fleet_row, "subscription_status": "TRIAL",
           "trial_ends_at": datetime(2026, 8, 30, tzinfo=timezone.utc),
           "next_billing_date": date(2026, 9, 30)}
    ctx = email_client.manager_onboarding_email_context(
        manager_full_name="Ravi", manager_username="ravi",
        temporary_password="pw", fleet=row, login_url="https://x/login",
    )
    assert ctx["subscription_expiry"].startswith("2026-08-30")


@pytest.mark.anyio
async def test_send_manager_onboarding_email_renders_and_posts(monkeypatch, fleet_row):
    """The async onboarding email renders via Jinja2 and sends with right data.

    We override the low-level HTTP sender so no network call happens; assert the
    rendered HTML and text embed the manager's credentials.
    """
    captured = {}

    async def fake_send_email(**kwargs):
        captured.update(kwargs)
        return {"status": "sent", "error": None}

    monkeypatch.setattr(email_client, "send_email", fake_send_email)
    setattr(email_client, "_is_email_configured", lambda: True)

    result = await email_client.send_manager_onboarding_email(
        to_email="ravi@manager.example",
        manager_name="Ravi Kumar",
        username="ravi",
        temporary_password="s3cret",
        login_url="https://app.vahankhata.com/login",
        fleet_name="Arvind Srivastava",
        subscription_plan="Monthly \u20b9799 Plan",
        subscription_expiry="2026-09-18",
        vehicle_limit=3,
        driver_limit=4,
    )
    assert result["status"] == "sent"
    assert captured["to_email"] == "ravi@manager.example"
    assert "Ravi Kumar" in captured["html_body"]
    assert "s3cret" in captured["html_body"]
    assert "ravi" in captured["html_body"]
    assert "s3cret" in captured["body"]


def test_sync_wrapper_skips_when_no_password_or_email(monkeypatch, fleet_row):
    """Fire-and-forget sync wrapper short-circuits without valid data."""
    call_count = {"n": 0}

    def fake_dispatch(fn, **kwargs):
        call_count["n"] += 1
        return {"status": "queued", "error": None, "queued": True}

    monkeypatch.setattr(email_client, "dispatch_sync", fake_dispatch)

    assert email_client.send_manager_onboarding_email_sync(
        to_email="", manager_name="R", username="u", temporary_password="pw",
        login_url="https://x/login", fleet_name="f", subscription_plan="Plan",
        subscription_expiry="x", vehicle_limit=1, driver_limit=1,
    )["status"] == "skipped"
    assert email_client.send_manager_onboarding_email_sync(
        to_email="m@x.com", manager_name="R", username="u", temporary_password="",
        login_url="https://x/login", fleet_name="f", subscription_plan="Plan",
        subscription_expiry="x", vehicle_limit=1, driver_limit=1,
    )["status"] == "skipped"
    assert call_count["n"] == 0