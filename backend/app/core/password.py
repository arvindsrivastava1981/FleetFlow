"""Password hashing — PBKDF2 (stdlib hashlib, no external deps).

Format: ``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """Return a PBKDF2 hash string for *password* with a random salt."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Constant-time comparison of *password* against *stored_hash*."""
    try:
        algo, iterations, salt_hex, hash_hex = stored_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(dk, expected)
    except (ValueError, AttributeError):
        return False

