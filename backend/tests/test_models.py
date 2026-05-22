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


def test_economics_overview_model_roundtrips():
    from app.models import (EconomicsOverview, IndicatorPoint,
                            IndicatorSummary, ReleaseEvent)
    ov = EconomicsOverview(
        indicators=[IndicatorSummary(
            series_id="UNRATE", name="Unemployment Rate", unit="%",
            latest=4.1, latest_date="2026-04-01", change=-0.1,
            trend="in", sparkline=[4.3, 4.2, 4.1])],
        calendar=[ReleaseEvent(date="2026-05-13",
                               release_name="Consumer Price Index")],
        updated_at="2026-05-21T00:00:00+00:00")
    assert ov.indicators[0].series_id == "UNRATE"
    assert ov.calendar[0].release_name == "Consumer Price Index"
    pt = IndicatorPoint(date="2026-04-01", value=4.1)
    assert pt.value == 4.1


def test_indicator_detail_model():
    from app.models import (IndicatorDetail, IndicatorPoint, RecessionSignal)
    detail = IndicatorDetail(
        series_id="UNRATE", name="Unemployment Rate", unit="%",
        series=[IndicatorPoint(date="2026-03-01", value=4.2),
                IndicatorPoint(date="2026-04-01", value=4.1)],
        latest=4.1, change=-0.1, yoy=0.3, range_low=3.4, range_high=4.3,
        momentum=-2.4,
        recession_signals=[RecessionSignal(
            name="Yield curve (10y-2y)", value=-0.15, status="alert",
            detail="Inverted — historically a recession precursor.")],
        updated_at="2026-05-21T00:00:00+00:00")
    assert detail.yoy == 0.3
    assert detail.recession_signals[0].status == "alert"
