"""Authentication helpers for NutriMind AI.

Password hashing uses PBKDF2-HMAC-SHA256 (stdlib `hashlib`) with a per-user
random salt — no third-party crypto dependency, which keeps the project
zero-cost and easy to set up. Session tokens are random, opaque, and stored
server-side in the `sessions` table (see database.py).
"""
from __future__ import annotations
import hashlib
import hmac
import os
import secrets

_PBKDF2_ROUNDS = 200_000
_ALGO = "sha256"


def hash_password(password: str) -> tuple[str, str]:
    """Return (salt_hex, hash_hex) for a new password."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(_ALGO, password.encode(), salt, _PBKDF2_ROUNDS)
    return salt.hex(), dk.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    """Constant-time check of a password against a stored salt+hash."""
    try:
        salt = bytes.fromhex(salt_hex)
    except (ValueError, TypeError):
        return False
    dk = hashlib.pbkdf2_hmac(_ALGO, password.encode(), salt, _PBKDF2_ROUNDS)
    return hmac.compare_digest(dk.hex(), hash_hex)


def new_session_token() -> str:
    """Cryptographically-random opaque session token."""
    return secrets.token_urlsafe(32)
