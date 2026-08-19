"""Application configuration — env-driven, fail-fast.

Replaces the flat `os.getenv` reads previously hoisted at module-import time in
`utils.py`. Two production invariants:
1. DATABASE_URL is required — fail loudly at startup, never silently run against a
   missing variable (fixes the masking risk flagged in deep_agent_recommendation §5).
2. Auth is per-user: login validates username + password against the `users` table.
   USER_PASSWORD env is deprecated (kept for backwards-compat only).


Access anywhere as:  from backend.app.core.config import settings

All values are read once at import time so the app boots deterministically and a
missing required var raises a clear error instead of half-initializing.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()  # idempotent; no-op when vars already present in the environment


class Settings:
    """Typed, fail-fast configuration holder for VahanKhata."""

    def __init__(self) -> None:
        # ---- Database -----------------------------------------------------
        self.database_url: str = _require("DATABASE_URL")

        # ----  auth ----------------------------------------------------
        # Per-user login replaces the single USER_PASSWORD. The env var is
        # still read for backwards-compat but is no longer used for login.
        default_password = "123"
        _ = os.getenv("USER_PASSWORD", default_password)  # deprecated, kept for compat
        self.auth_cookie: str = "ff_auth_session"

        # ---- Session / security -------------------------------------------
        self.session_ttl_hours: int = 72
        self.login_max_attempts: int = 5
        self.login_lockout_seconds: int = 300

        # ---- Rules-engine thresholds (single source of truth) --------------
        self.benchmark_price: float = 90.50
        self.tank_capacity_liters: float = 350.0
        self.expected_kml: float = 4.0
        self.def_rate_max: float = 75.0
        self.def_min_ratio_pct: float = 3.0
        self.def_max_ratio_pct: float = 6.0
        self.math_tolerance: float = 10.0
        self.fuel_band_tolerance_pct: float = 0.08

        # ---- System Invariants (from APP_MINDMAP) --------------------------
        self.plate_regex: str = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$"
        self.country_code: str = "+91"
        self.qr_code_length: int = 6
        self.anti_spam_scans_per_hour: int = 3

        # ---- Email (Resend) ---------------------------------------------------
        self.resend_api_key: str | None = os.getenv("RESEND_API_KEY")
        self.sender_email: str | None = os.getenv("SENDER_EMAIL")
        self.support_email: str = os.getenv("SUPPORT_EMAIL", "support@vahankhata.com")

        # ---- WhatsApp (Phase C) & OCR (Phase D) ----------------------------
        self.whatsapp_access_token: str | None = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.whatsapp_phone_id: str | None = os.getenv("WHATSAPP_PHONE_ID")
        self.webhook_verify_token: str | None = os.getenv("WEBHOOK_VERIFY_TOKEN")

        # ---- Razorpay billing (subscription + per-vehicle payments) --------
        self.razorpay_key_id: str | None = os.getenv("RAZORPAY_API_KEY")
        self.razorpay_key_secret: str | None = os.getenv("RAZORPAY_API_SECRET")
        self.razorpay_webhook_secret: str | None = os.getenv("RAZORPAY_WEBHOOK_SECRET")
        self.razorpay_test_mode: bool = (
            os.getenv("RAZORPAY_TEST_MODE", "1").strip().lower() in ("1", "true", "yes")
        )


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Set it in .env or the deployment environment before starting."
        )
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide singleton `Settings` instance."""
    return Settings()


settings = get_settings()