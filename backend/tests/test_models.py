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


def test_technicals_new_fields_default_empty():
    from app.models import Technicals
    t = Technicals(sma_20=[1.0], sma_50=[None], sma_200=[None])
    assert t.rsi == []
    assert t.macd_line == []
    assert t.bb_upper == []
    assert t.volume == []


def test_returns_model():
    from app.models import Returns
    r = Returns(week_1=1.5, ytd=3.0)
    assert r.week_1 == 1.5
    assert r.ytd == 3.0
    assert r.year_3 is None


def test_markets_response_model():
    from app.models import (AssetClass, Breadth, MarketsResponse, Mover,
                            SectorChange, WatchlistQuote)
    markets = MarketsResponse(
        asset_classes=[AssetClass(label="Crypto", symbol="BTC-USD",
                                  price=1.0, change_pct=2.0,
                                  sparkline=[1.0, 2.0])],
        indices=[WatchlistQuote(symbol="^GSPC", price=1.0, change=0.1,
                                change_pct=1.0, volume=1,
                                as_of="2026-01-02", sparkline=[1.0])],
        gainers=[Mover(symbol="AAA", price=2.0, change_pct=9.0)],
        losers=[Mover(symbol="BBB", price=2.0, change_pct=-9.0)],
        sectors=[SectorChange(symbol="XLK", name="Tech", change_pct=1.0)],
        breadth=Breadth(advancers=1, decliners=1, unchanged=0,
                        advance_decline_ratio=1.0),
        updated_at="2026-01-02T00:00:00Z")
    assert markets.asset_classes[0].label == "Crypto"
    assert markets.gainers[0].change_pct == 9.0
    assert markets.losers[0].symbol == "BBB"


def test_recession_period_model():
    from app.models import RecessionPeriod
    p = RecessionPeriod(start="2020-02-01", end="2020-04-01")
    assert p.start == "2020-02-01"
    assert p.end == "2020-04-01"


def test_indicator_summary_has_optional_category():
    from app.models import IndicatorSummary
    s = IndicatorSummary(
        series_id="CPIAUCSL", name="Inflation (CPI)", unit="%",
        category="Inflation", latest=3.0, latest_date="2026-04-01",
        change=0.1, trend="in", sparkline=[1.0, 2.0])
    assert s.category == "Inflation"
    # category defaults to "" so older constructions stay valid
    s2 = IndicatorSummary(
        series_id="UNRATE", name="Unemployment Rate", unit="%", latest=4.0,
        latest_date="2026-04-01", change=0.0, trend="in", sparkline=[1.0])
    assert s2.category == ""


def test_indicator_detail_has_recession_periods_default():
    from app.models import IndicatorDetail
    d = IndicatorDetail(
        series_id="UNRATE", name="Unemployment Rate", unit="%", series=[],
        latest=4.0, change=0.0, range_low=3.0, range_high=5.0, momentum=0.0,
        recession_signals=[], updated_at="t")
    assert d.recession_periods == []


def test_economics_dashboard_model():
    from app.models import (EconomicsDashboard, IndicatorCategory,
                            IndicatorSummary)
    summary = IndicatorSummary(
        series_id="CPIAUCSL", name="Inflation (CPI)", unit="%",
        category="Inflation", latest=3.0, latest_date="2026-04-01",
        change=0.1, trend="in", sparkline=[1.0, 2.0])
    cat = IndicatorCategory(name="Inflation", indicators=[summary])
    dash = EconomicsDashboard(categories=[cat], recession_signals=[],
                              calendar=[], updated_at="t")
    assert dash.categories[0].name == "Inflation"
    assert dash.categories[0].indicators[0].category == "Inflation"


def test_news_models_round_trip():
    from app.models import (Article, MomentumPoint, NewsOverview, StoryCluster,
                            StoryDetail)
    art = Article(id="a1", title="A headline", summary="A summary",
                  url="https://ex.com/1", source="Example News",
                  published_at="2026-05-22T10:00:00+00:00", category="general")
    cluster = StoryCluster(id="c1", headline="A headline", summary="A summary",
                           category="general", source_count=3, article_count=5,
                           momentum=1.8, status="surging",
                           latest_published_at="2026-05-22T11:00:00+00:00")
    overview = NewsOverview(stories=[cluster],
                            updated_at="2026-05-22T12:00:00+00:00")
    detail = StoryDetail(
        id="c1", headline="A headline", summary="A summary", category="general",
        source_count=3, article_count=5, momentum=1.8, status="surging",
        articles=[art],
        momentum_series=[MomentumPoint(time="2026-05-22T10:00:00+00:00",
                                       count=2)],
        related=[cluster], updated_at="2026-05-22T12:00:00+00:00")
    assert overview.stories[0].id == "c1"
    assert detail.articles[0].source == "Example News"
    assert detail.momentum_series[0].count == 2
    assert detail.related[0].status == "surging"
    assert art.image_url is None
