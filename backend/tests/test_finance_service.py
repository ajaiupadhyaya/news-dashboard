from app.models import Bar, Fundamentals, Quote
from app.providers import yfinance_provider
from app.services import finance_service


def _bars(closes: list[float]) -> list[Bar]:
    return [
        Bar(date=f"2026-01-{i + 1:02d}", open=c, high=c + 1, low=c - 1,
            close=c, volume=1000)
        for i, c in enumerate(closes)
    ]


def test_build_overview_assembles_watchlist_and_breadth(db, monkeypatch):
    monkeypatch.setenv("WATCHLIST_DEFAULT", "AAPL")
    monkeypatch.setattr(yfinance_provider, "get_history",
                        lambda *a, **k: _bars([100.0, 101.0, 102.0]))
    monkeypatch.setattr(yfinance_provider, "get_quote",
                        lambda sym: Quote(symbol=sym, price=10.0, change=0.5,
                                          change_pct=1.0, volume=1,
                                          as_of="2026-01-03"))
    overview = finance_service.build_overview()
    assert len(overview.watchlist) == 1
    assert overview.watchlist[0].symbol == "AAPL"
    assert overview.watchlist[0].sparkline  # non-empty
    assert overview.breadth.advancers > 0
    assert overview.updated_at


def test_build_instrument_returns_bars_and_technicals(db, monkeypatch):
    closes = [100.0 + i for i in range(60)]
    monkeypatch.setattr(yfinance_provider, "get_history",
                        lambda *a, **k: _bars(closes))
    monkeypatch.setattr(yfinance_provider, "get_fundamentals",
                        lambda sym: Fundamentals(symbol=sym, name="Test Co"))
    result = finance_service.build_instrument("aapl")
    assert result is not None
    assert result.symbol == "AAPL"
    assert len(result.bars) == 60
    assert len(result.technicals.sma_20) == 60
    assert result.profile.name == "Test Co"
    assert result.stats.momentum_1m != 0.0


def test_build_instrument_none_when_no_data(db, monkeypatch):
    monkeypatch.setattr(yfinance_provider, "get_history", lambda *a, **k: [])
    assert finance_service.build_instrument("ZZZZ") is None
