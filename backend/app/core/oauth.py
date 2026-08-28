"""Social identity verification for Google / Facebook sign-in.

The frontend obtains the provider credential (Google GIS ID token or a
Facebook access token) and POSTs it to /api/v1/auth/{google|facebook}. Here we
verify the credential **server-side** against the provider before issuing a
VahanKhata session — we never trust the client-supplied identity on its own.
"""
from __future__ import annotations

import urllib.parse
import urllib.request

from backend.app.core.config import settings


class SocialAuthError(Exception):
    """Raised when a provider credential is missing, forged, or unverifiable."""


def _http_json(url: str, timeout: float = 8.0) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as res:  # noqa: S310
            return dict(__import__("json").loads(res.read().decode("utf-8")))
    except Exception as exc:  # noqa: BLE001
        raise SocialAuthError(f"provider request failed: {exc}") from exc


def verify_google_id_token(credential: str) -> dict:
    """Validate a Google ID token and return {sub, email, name, picture}.

    Uses Google's tokeninfo endpoint (signature verified by Google itself);
    `aud` must match GOOGLE_CLIENT_ID and the token must be currently valid.
    """
    if not settings.google_client_id:
        raise SocialAuthError("google login is not configured")
    if not credential:
        raise SocialAuthError("missing google credential")
    info = _http_json(
        "https://oauth2.googleapis.com/tokeninfo?"
        + urllib.parse.urlencode({"id_token": credential})
    )
    if info.get("aud") != settings.google_client_id:
        raise SocialAuthError("google token audience mismatch")
    if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise SocialAuthError("google token issuer mismatch")
    sub, email = info.get("sub"), (info.get("email") or "").strip().lower()
    if not sub or not email:
        raise SocialAuthError("google token missing sub/email")
    return {"sub": sub, "email": email, "name": info.get("name") or email, "picture": info.get("picture")}


def verify_facebook_token(access_token: str) -> dict:
    """Validate a Facebook access token and return {sub, email, name, picture}."""
    if not settings.facebook_app_id or not settings.facebook_app_secret:
        raise SocialAuthError("facebook login is not configured")
    if not access_token:
        raise SocialAuthError("missing facebook access token")
    app_token = f"{settings.facebook_app_id}|{settings.facebook_app_secret}"
    debug = _http_json(
        "https://graph.facebook.com/debug_token?"
        + urllib.parse.urlencode(
            {"input_token": access_token, "access_token": app_token}
        )
    )
    data = debug.get("data") or {}
    if not data.get("is_valid"):
        raise SocialAuthError("facebook token is invalid or expired")
    if data.get("app_id") != settings.facebook_app_id:
        raise SocialAuthError("facebook token app mismatch")
    profile = _http_json(
        "https://graph.facebook.com/me?"
        + urllib.parse.urlencode(
            {
                "fields": "id,name,email",
                "access_token": access_token,
            }
        )
    )
    sub, email = profile.get("id"), (profile.get("email") or "").strip().lower()
    if not sub:
        raise SocialAuthError("facebook profile missing id")
    return {
        "sub": sub,
        "email": email or f"{sub}@facebook.local",
        "name": profile.get("name") or email or sub,
        "picture": None,
    }
