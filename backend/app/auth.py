from fastapi import Header, HTTPException

from app.config import get_settings


def login(password: str) -> str:
    """Exchange a password for the shared token. When no password is
    configured, login always succeeds (local dev)."""
    settings = get_settings()
    if settings.dashboard_password and password != settings.dashboard_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    return settings.dashboard_token or "open"


def require_auth(authorization: str | None = Header(default=None)) -> None:
    """FastAPI dependency. No-op when DASHBOARD_TOKEN is unset; otherwise
    requires `Authorization: Bearer <DASHBOARD_TOKEN>`."""
    settings = get_settings()
    if not settings.dashboard_token:
        return
    if authorization != f"Bearer {settings.dashboard_token}":
        raise HTTPException(status_code=401, detail="Not authenticated")
