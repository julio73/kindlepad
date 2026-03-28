"""Authentication dependency for FastAPI."""

from __future__ import annotations

import hmac

from fastapi import Depends, HTTPException, Request


def require_auth(request: Request) -> None:
    """Validate the Bearer token from the Authorization header."""
    token = request.app.state.config.server.token
    if not token:
        # No token configured — skip auth.
        return

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    provided = auth_header.removeprefix("Bearer ")
    if not hmac.compare_digest(provided.encode(), token.encode()):
        raise HTTPException(status_code=401, detail="Invalid token")
