"""
Admin API key authentication dependency.

Usage:
    from app.dependencies.auth import verify_admin

    @router.get("/protected")
    async def endpoint(admin=Depends(verify_admin)):
        ...

Requires the request header:
    x-api-key: <value of ADMIN_API_KEY env var>

Returns HTTP 401 if the key is missing or incorrect.
"""

import os
import secrets
from typing import Optional
from fastapi import Header, HTTPException


def verify_admin(x_api_key: Optional[str] = Header(default=None, alias="x-api-key")) -> None:
    """
    FastAPI dependency that validates the x-api-key header against ADMIN_API_KEY.
    Raises 401 if the key is absent or does not match.
    """
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: ADMIN_API_KEY is not set.",
        )
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing API key.")
