"""WebSocket JWT validation."""
from typing import Optional

from app.auth.jwt import decode_token

UNAUTHORIZED_CLOSE = 4401


def validate_ws_token(token: Optional[str]) -> Optional[str]:
    """Return user_id if access token is valid, else None."""
    if not token or not token.strip():
        return None
    payload = decode_token(token.strip())
    if not payload or payload.get("type") != "access":
        return None
    return payload.get("sub")
