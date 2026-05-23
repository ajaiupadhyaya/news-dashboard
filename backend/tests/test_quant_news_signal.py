import pandas as pd
from sqlalchemy import insert

from app.database import get_engine, news_articles, news_clusters
from app.quant.news_signal import news_coverage_matrix, top_news_universe


def _seed_articles(db, articles):
    with get_engine().begin() as conn:
        conn.execute(insert(news_articles), articles)


def test_news_coverage_matrix_counts_per_symbol_per_day(db):
    arts = [
        {"id": "a1", "cluster_id": None, "title": "AAPL beats earnings",
         "summary": "Apple inc beat estimates", "url": "x", "source": "Reuters",
         "published_at": "2026-05-01T10:00:00Z", "category": "finance",
         "image_url": None},
        {"id": "a2", "cluster_id": None, "title": "AAPL up after iPhone reveal",
         "summary": "", "url": "x", "source": "Bloomberg",
         "published_at": "2026-05-01T14:00:00Z", "category": "finance",
         "image_url": None},
        {"id": "a3", "cluster_id": None, "title": "MSFT cloud growth",
         "summary": "Microsoft Azure", "url": "x", "source": "Reuters",
         "published_at": "2026-05-01T11:00:00Z", "category": "finance",
         "image_url": None},
    ]
    _seed_articles(db, arts)
    df = news_coverage_matrix(
        symbols=["AAPL", "MSFT", "TSLA"],
        start="2026-05-01", end="2026-05-02",
    )
    assert df.loc["2026-05-01", "AAPL"] == 2
    assert df.loc["2026-05-01", "MSFT"] == 1
    assert df.loc["2026-05-01", "TSLA"] == 0


def test_top_news_universe_ranks_by_rolling_coverage(db):
    arts = [
        {"id": f"a{i}", "cluster_id": None,
         "title": "AAPL " * 10, "summary": "Apple",
         "url": "x", "source": "Reuters",
         "published_at": f"2026-05-{(i % 5) + 1:02d}T10:00:00Z",
         "category": "finance", "image_url": None}
        for i in range(20)
    ] + [
        {"id": "m1", "cluster_id": None,
         "title": "MSFT cloud", "summary": "Microsoft",
         "url": "x", "source": "Reuters",
         "published_at": "2026-05-03T10:00:00Z",
         "category": "finance", "image_url": None},
    ]
    _seed_articles(db, arts)
    top = top_news_universe(
        candidate_symbols=["AAPL", "MSFT", "TSLA", "NVDA"],
        as_of="2026-05-05", lookback_days=7, top_n=2,
    )
    assert top[0] == "AAPL"
    assert "MSFT" in top
