from app import scheduler
from app.cache import cache
from app.models import Bar, Quote
from app.providers import yfinance_provider


def test_start_scheduler_returns_none_when_disabled(monkeypatch):
    monkeypatch.delenv("SCHEDULER_ENABLED", raising=False)
    assert scheduler.start_scheduler() is None


def test_warm_overview_populates_cache(db, monkeypatch):
    monkeypatch.setenv("WATCHLIST_DEFAULT", "AAPL")
    monkeypatch.setattr(
        yfinance_provider, "get_history",
        lambda *a, **k: [Bar(date="2026-01-02", open=1, high=2, low=1,
                              close=1.5, volume=10)])
    monkeypatch.setattr(
        yfinance_provider, "get_quote",
        lambda sym: Quote(symbol=sym, price=1.0, change=0.0, change_pct=0.0,
                          volume=1, as_of="2026-01-02"))
    assert cache.get("finance:overview") is None
    scheduler.warm_overview()
    assert cache.get("finance:overview") is not None


def test_start_scheduler_is_idempotent(monkeypatch):
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    try:
        first = scheduler.start_scheduler()
        second = scheduler.start_scheduler()
        assert first is not None
        assert first is second
    finally:
        scheduler.shutdown_scheduler()
