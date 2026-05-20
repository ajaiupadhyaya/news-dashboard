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
