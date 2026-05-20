import pytest

from app.config import get_settings


def test_defaults_when_env_unset(monkeypatch):
    for var in ("DATABASE_URL", "DASHBOARD_TOKEN", "DASHBOARD_PASSWORD",
                "SCHEDULER_ENABLED", "CACHE_TTL_SECONDS", "WATCHLIST_DEFAULT", "LOG_LEVEL"):
        monkeypatch.delenv(var, raising=False)
    s = get_settings()
    assert s.database_url is None
    assert s.dashboard_token is None
    assert s.scheduler_enabled is False
    assert s.cache_ttl_seconds == 300
    assert s.watchlist_default == ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]
    assert s.cors_origins == ["*"]
    assert s.log_level == "INFO"


def test_reads_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "60")
    monkeypatch.setenv("WATCHLIST_DEFAULT", "TSLA, AMD")
    monkeypatch.setenv("CORS_ORIGINS", "https://a.com, https://b.com")
    s = get_settings()
    assert s.database_url == "postgresql://x"
    assert s.scheduler_enabled is True
    assert s.cache_ttl_seconds == 60
    assert s.watchlist_default == ["TSLA", "AMD"]
    assert s.cors_origins == ["https://a.com", "https://b.com"]


def test_invalid_cache_ttl_raises(monkeypatch):
    monkeypatch.setenv("CACHE_TTL_SECONDS", "not-a-number")
    with pytest.raises(ValueError, match="CACHE_TTL_SECONDS"):
        get_settings()
