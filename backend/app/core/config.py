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
        self.auth_cookie: str = "ff_auth_session"
        # Secure-cookie flag for the session cookie (audit B-6). Defaults ON;
        # set COOKIE_SECURE=0 only for plain-HTTP local dev over a LAN IP
        # (localhost is exempt — browsers treat it as a trustworthy origin).
        self.cookie_secure: bool = (
            os.getenv("COOKIE_SECURE", "1").strip().lower() not in ("0", "false", "no")
        )

        self.auth_cookie_enabled: bool = (
            os.getenv("AUTH_COOKIE", "0").strip().lower() in ("1", "true", "yes")
        )

        # ---- HTTP / CORS (audit R-5) --------------------------------------
        # A CORS_ORIGINS CSV overrides; otherwise fall back to the historical
        # allowlist (prod hosts + local Vite dev server).
        self.cors_origins: list[str] = [
            o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
        ] or [
            "https://app.vahankhata.in",
            "https://api.vahankhata.in",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

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
        self.support_email: str = os.getenv("SUPPORT_EMAIL", "support@vahankhata.in")
        self.app_public_url: str = os.getenv("APP_PUBLIC_URL", "")

        # ---- WhatsApp (Phase C) & OCR (Phase D) ----------------------------
        self.whatsapp_access_token: str | None = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.whatsapp_phone_id: str | None = os.getenv("WHATSAPP_PHONE_ID")
        self.webhook_verify_token: str | None = os.getenv("WEBHOOK_VERIFY_TOKEN")
        # Meta App Secret — enables X-Hub-Signature-256 verification on the
        # inbound WhatsApp webhook (audit B-2). Optional until configured.
        self.whatsapp_app_secret: str | None = os.getenv("WHATSAPP_APP_SECRET")

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
