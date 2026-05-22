from app.database import save_ohlcv, load_ohlcv
from app.models import Bar


def _bar(date: str, close: float) -> Bar:
    return Bar(date=date, open=close, high=close + 1, low=close - 1,
               close=close, volume=1000)


def test_save_and_load_ohlcv(db):
    save_ohlcv("AAPL", [_bar("2026-01-02", 100.0), _bar("2026-01-03", 101.0)])
    rows = load_ohlcv("AAPL")
    assert [r.date for r in rows] == ["2026-01-02", "2026-01-03"]
    assert rows[1].close == 101.0


def test_save_ohlcv_replaces_previous_rows(db):
    save_ohlcv("AAPL", [_bar("2026-01-02", 100.0)])
    save_ohlcv("AAPL", [_bar("2026-01-03", 105.0), _bar("2026-01-04", 106.0)])
    rows = load_ohlcv("AAPL")
    assert [r.date for r in rows] == ["2026-01-03", "2026-01-04"]


def test_load_ohlcv_unknown_symbol_returns_empty(db):
    assert load_ohlcv("ZZZZ") == []


def test_econ_series_round_trips(db):
    from app.database import load_econ_series, save_econ_series
    from app.models import IndicatorPoint
    points = [IndicatorPoint(date="2026-01-01", value=2.9),
              IndicatorPoint(date="2026-02-01", value=3.1)]
    save_econ_series("CPIAUCSL", points)
    loaded = load_econ_series("CPIAUCSL")
    assert [p.date for p in loaded] == ["2026-01-01", "2026-02-01"]
    assert loaded[1].value == 3.1


def test_save_econ_series_replaces_prior(db):
    from app.database import load_econ_series, save_econ_series
    from app.models import IndicatorPoint
    save_econ_series("UNRATE", [IndicatorPoint(date="2026-01-01", value=4.0)])
    save_econ_series("UNRATE", [IndicatorPoint(date="2026-02-01", value=4.1)])
    loaded = load_econ_series("UNRATE")
    assert len(loaded) == 1 and loaded[0].date == "2026-02-01"


def test_save_and_load_news(db):
    from app.database import (ClusterRecord, load_news_cluster,
                              load_news_clusters, save_news)
    from app.models import Article
    art = Article(id="a1", title="Headline", summary="Summary",
                  url="https://ex.com/1", source="Example",
                  published_at="2026-05-22T10:00:00+00:00", category="general")
    rec = ClusterRecord(
        id="c1", headline="Headline", summary="Summary", category="general",
        source_count=1, article_count=1, momentum=2.0, status="surging",
        first_published_at="2026-05-22T10:00:00+00:00",
        latest_published_at="2026-05-22T10:00:00+00:00",
        centroid=[0.1, 0.2], rank_order=0, articles=[art])
    save_news([rec])

    clusters = load_news_clusters()
    assert len(clusters) == 1
    assert clusters[0].id == "c1"
    assert clusters[0].articles == []          # list loader omits articles

    full = load_news_cluster("c1")
    assert full is not None
    assert full.centroid == [0.1, 0.2]
    assert full.articles[0].id == "a1"


def test_save_news_replaces_previous_snapshot(db):
    from app.database import ClusterRecord, load_news_clusters, save_news

    def rec(cid):
        return ClusterRecord(
            id=cid, headline="H", summary="S", category="general",
            source_count=1, article_count=1, momentum=1.0, status="steady",
            first_published_at="2026-05-22T10:00:00+00:00",
            latest_published_at="2026-05-22T10:00:00+00:00",
            centroid=[], rank_order=0, articles=[])

    save_news([rec("c1")])
    save_news([rec("c2")])
    ids = {c.id for c in load_news_clusters()}
    assert ids == {"c2"}


def test_load_news_cluster_missing_returns_none(db):
    from app.database import load_news_cluster
    assert load_news_cluster("nope") is None
