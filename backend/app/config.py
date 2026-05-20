import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    dashboard_token: str | None
    dashboard_password: str | None
    scheduler_enabled: bool
    log_level: str
    cors_origins: list[str]
    cache_ttl_seconds: int
    watchlist_default: list[str]


def _env_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_settings() -> Settings:
    """Read settings from the environment on every call (no caching) so tests
    that mutate env vars see fresh values."""
    return Settings(
        database_url=os.getenv("DATABASE_URL") or None,
        dashboard_token=os.getenv("DASHBOARD_TOKEN") or None,
        dashboard_password=os.getenv("DASHBOARD_PASSWORD") or None,
        scheduler_enabled=os.getenv("SCHEDULER_ENABLED", "false").strip().lower()
        in ("1", "true", "yes"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        cors_origins=_env_list("CORS_ORIGINS", "*"),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "300")),
        watchlist_default=_env_list("WATCHLIST_DEFAULT", "AAPL,MSFT,NVDA,GOOGL,AMZN"),
    )
