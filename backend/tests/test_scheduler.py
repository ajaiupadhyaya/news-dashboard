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


def test_warm_economics_populates_cache(db, monkeypatch):
    from app.cache import cache
    from app.providers import fred_provider
    from app.models import IndicatorPoint
    from app import scheduler

    monkeypatch.setattr(fred_provider, "get_series",
                        lambda sid, **kw: [IndicatorPoint(
                            date=f"2026-0{i+1}-01", value=100.0 + i)
                            for i in range(5)])
    monkeypatch.setattr(fred_provider, "get_release_calendar", lambda: [])
    scheduler.warm_economics()
    assert cache.get("economics:overview") is not None
    assert cache.get("economics:dashboard") is not None


def test_warm_markets_populates_cache(db, monkeypatch):
    from app.cache import cache
    from app.models import Bar, Quote
    from app.providers import yfinance_provider

    monkeypatch.setattr(
        yfinance_provider, "get_history",
        lambda *a, **k: [Bar(date="2026-01-02", open=1, high=2, low=1,
                              close=1.5, volume=10),
                         Bar(date="2026-01-03", open=1, high=2, low=1,
                             close=1.6, volume=10)])
    monkeypatch.setattr(
        yfinance_provider, "get_quote",
        lambda sym: Quote(symbol=sym, price=1.0, change=0.0, change_pct=0.0,
                          volume=1, as_of="2026-01-03"))
    scheduler.warm_markets()
    assert cache.get("finance:markets") is not None


def test_warm_news_populates_cache(db, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.cache import cache
    from app.models import Article
    from app.providers import news_api_provider, rss_provider
    from app.services import embeddings

    now = datetime.now(timezone.utc)
    articles = [
        Article(id=f"a{i}", title=f"Story {i}", summary="summary",
                url=f"https://ex.com/{i}", source=f"Source {i}",
                published_at=(now - timedelta(hours=i + 1)).isoformat(),
                category="general")
        for i in range(3)
    ]
    monkeypatch.setattr(rss_provider, "get_articles", lambda: articles)
    monkeypatch.setattr(news_api_provider, "get_articles", lambda: [])
    monkeypatch.setattr(embeddings, "embed",
                        lambda texts: [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]])
    scheduler.warm_news()
    assert cache.get("news:overview") is not None


def test_quant_jobs_registered(monkeypatch):
    """Verify that warm_quant_bars and forward_step_all_strategies are registered."""
    monkeypatch.setenv("SCHEDULER_ENABLED", "true")
    s = scheduler.start_scheduler()
    try:
        ids = {job.id for job in s.get_jobs()}
        assert "warm_quant_bars" in ids
        assert "forward_step_all_strategies" in ids
    finally:
        scheduler.shutdown_scheduler()
