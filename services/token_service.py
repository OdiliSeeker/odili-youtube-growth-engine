"""
HMAC token utilities for one-click unsubscribe links.

Tokens are derived from the recipient's email + SESSION_SECRET, so no DB
storage is needed and links remain valid indefinitely unless the secret rotates.
"""

import hmac
import hashlib
import os
from urllib.parse import quote


def _get_secret() -> bytes:
    secret = os.getenv("SESSION_SECRET", "odili-default-secret-please-set-SESSION_SECRET")
    return secret.encode()


def make_unsubscribe_token(email: str) -> str:
    """Return a hex HMAC-SHA256 token for the given email address."""
    return hmac.new(_get_secret(), email.strip().lower().encode(), hashlib.sha256).hexdigest()


def verify_unsubscribe_token(email: str, token: str) -> bool:
    """Constant-time comparison — safe against timing attacks."""
    expected = make_unsubscribe_token(email.strip().lower())
    try:
        return hmac.compare_digest(expected, token)
    except (TypeError, ValueError):
        return False


def get_base_url() -> str:
    """
    Resolve the public-facing base URL for link generation.
    Priority: REPLIT_DOMAINS (production) → REPLIT_DEV_DOMAIN (dev preview) → localhost.
    """
    domains = os.getenv("REPLIT_DOMAINS", "")
    if domains:
        return "https://" + domains.split(",")[0].strip()
    dev = os.getenv("REPLIT_DEV_DOMAIN", "")
    if dev:
        return "https://" + dev.strip()
    return "http://localhost:8000"


def make_unsubscribe_url(email: str) -> str:
    """Build a signed one-click unsubscribe URL for the given address."""
    token = make_unsubscribe_token(email)
    return f"{get_base_url()}/unsubscribe?email={quote(email)}&token={token}"
