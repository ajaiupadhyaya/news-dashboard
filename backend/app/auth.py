import hmac

from fastapi import Header, HTTPException

from app.config import get_settings


def login(password: str) -> str:
    """Exchange a password for the shared token.

    Both DASHBOARD_TOKEN and DASHBOARD_PASSWORD unset -> open mode (local dev).
    Exactly one set -> server misconfiguration. Both set -> verify the password.
    """
    settings = get_settings()
    if not settings.dashboard_token and not settings.dashboard_password:
        return "open"
    if not (settings.dashboard_token and settings.dashboard_password):
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: set both DASHBOARD_TOKEN and "
                   "DASHBOARD_PASSWORD, or neither",
        )
    if password != settings.dashboard_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    return settings.dashboard_token


def require_auth(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency. No-op when DASHBOARD_TOKEN is unset; otherwise
    requires `Authorization: Bearer <DASHBOARD_TOKEN>`."""
    settings = get_settings()
    if not settings.dashboard_token:
        return
    expected = f"Bearer {settings.dashboard_token}"
    if not hmac.compare_digest(authorization or "", expected):
        raise HTTPException(status_code=401, detail="Not authenticated")
