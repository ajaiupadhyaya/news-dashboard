from app.models import (
    Bar, Quote, WatchlistQuote, Fundamentals, SectorChange, Breadth,
    OverviewResponse, Technicals, InstrumentStats, InstrumentResponse,
)


def test_bar_and_quote_construct():
    bar = Bar(date="2026-01-02", open=1.0, high=2.0, low=0.5, close=1.5, volume=100)
    assert bar.close == 1.5
    quote = Quote(symbol="AAPL", price=1.5, change=0.1, change_pct=2.0,
                  volume=100, as_of="2026-01-02")
    assert quote.symbol == "AAPL"


def test_watchlist_quote_extends_quote_with_sparkline():
    wq = WatchlistQuote(symbol="AAPL", price=1.5, change=0.1, change_pct=2.0,
                        volume=100, as_of="2026-01-02", sparkline=[1.0, 1.5])
    assert wq.sparkline == [1.0, 1.5]
    assert wq.price == 1.5


def test_fundamentals_optional_fields_default_none():
    f = Fundamentals(symbol="AAPL", name="Apple")
    assert f.sector is None
    assert f.pe_ratio is None


def test_overview_response_assembles():
    resp = OverviewResponse(
        watchlist=[],
        indices=[],
        sectors=[SectorChange(symbol="XLK", name="Technology", change_pct=1.0)],
        breadth=Breadth(advancers=1, decliners=0, unchanged=0,
                        advance_decline_ratio=1.0),
        updated_at="2026-01-02T00:00:00Z",
    )
    assert resp.sectors[0].symbol == "XLK"


def test_instrument_response_assembles():
    resp = InstrumentResponse(
        symbol="AAPL",
        profile=Fundamentals(symbol="AAPL", name="Apple"),
        bars=[Bar(date="2026-01-02", open=1, high=2, low=1, close=1.5, volume=10)],
        technicals=Technicals(sma_20=[None], sma_50=[None], sma_200=[None]),
        stats=InstrumentStats(momentum_1m=1.0, momentum_3m=2.0, momentum_6m=3.0,
                              volatility_30d=10.0),
        updated_at="2026-01-02T00:00:00Z",
    )
    assert resp.symbol == "AAPL"
