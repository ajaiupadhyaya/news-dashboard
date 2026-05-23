"""Tests that inception_walkforward correctly builds and passes StrategyContext
to the alpha strategies (news-sentiment-momentum and macro-regime-overlay).
"""

import pandas as pd
from sqlalchemy import insert, select

from app.database import econ_series, get_engine, news_articles, strategy_runs
from app.quant.bars import upsert_bars
from app.quant.orchestration import inception_walkforward
from app.quant.strategies.base import StrategySpec
from app.quant.strategies.macro_regime_overlay import MacroRegimeOverlay
from app.quant.strategies.news_sentiment_momentum import NewsSentimentMomentum

# Seeded bar range: 2020-01-02 to approximately 2024-12-31 (5 years).
_BAR_START = "2020-01-02"
_BAR_END_APPROX = "2024-12-31"


def _seed_minimal_bars(years: int = 5):
    """Seed flat 100.0 prices for SPY + first 30 SP500 + defensive ETFs."""
    idx = pd.bdate_range(_BAR_START, periods=252 * years)
    from app.quant.universe import SP500_SYMBOLS
    universe = list(SP500_SYMBOLS[:30]) + ["SPY", "XLP", "XLU", "XLV"]
    for sym in universe:
        df = pd.DataFrame({
            "Open": 100.0, "High": 101.0, "Low": 99.0,
            "Close": 100.0, "Adj Close": 100.0, "Volume": 1_000_000,
        }, index=idx)
        upsert_bars(sym, df)


# ---------------------------------------------------------------------------
# Patched strategy subclasses with date ranges that match the seeded bars.
# StrategySpec is frozen, so we override `spec` at the class level.
# ---------------------------------------------------------------------------

class _NewsSentimentTest(NewsSentimentMomentum):
    spec = StrategySpec(
        slug="news-sentiment-momentum",
        name="News-Sentiment Momentum",
        category="alpha",
        universe_kind="news-top100",
        inception_date=_BAR_START,
        live_start_date=_BAR_END_APPROX,
        methodology_blurb=NewsSentimentMomentum.spec.methodology_blurb,
        allow_short=False,
    )


class _MacroRegimeTest(MacroRegimeOverlay):
    spec = StrategySpec(
        slug="macro-regime-overlay",
        name="Macro-Regime Overlay (Momentum)",
        category="alpha",
        universe_kind="sp500",
        inception_date=_BAR_START,
        live_start_date=_BAR_END_APPROX,
        methodology_blurb=MacroRegimeOverlay.spec.methodology_blurb,
        allow_short=False,
    )


def test_news_sentiment_orchestrator_does_not_crash(db):
    _seed_minimal_bars()
    with get_engine().begin() as conn:
        conn.execute(insert(news_articles), [
            {"id": "a1", "cluster_id": None, "title": "AAPL beats",
             "summary": "", "url": "x", "source": "Reuters",
             "published_at": "2024-12-01T10:00:00Z",
             "category": "finance", "image_url": None},
        ])
    s = _NewsSentimentTest()
    run_id = inception_walkforward(s, train_years=2, test_years=1, step_months=6,
                                    initial_equity=100_000)
    with get_engine().begin() as conn:
        row = conn.execute(
            select(strategy_runs).where(strategy_runs.c.id == run_id)
        ).first()
    assert row.status == "success"


def test_macro_regime_orchestrator_does_not_crash(db):
    _seed_minimal_bars()
    with get_engine().begin() as conn:
        conn.execute(insert(econ_series), [
            {"series_id": "T10Y2Y", "date": "2024-06-01", "value": -0.3},
            {"series_id": "UNRATE",  "date": "2024-05-01", "value": 4.0},
            {"series_id": "UNRATE",  "date": "2024-06-01", "value": 4.2},
            {"series_id": "INDPRO",  "date": "2024-05-01", "value": 100.0},
            {"series_id": "INDPRO",  "date": "2024-06-01", "value": 99.0},
        ])
    s = _MacroRegimeTest()
    run_id = inception_walkforward(s, train_years=2, test_years=1, step_months=6,
                                    initial_equity=100_000)
    with get_engine().begin() as conn:
        row = conn.execute(
            select(strategy_runs).where(strategy_runs.c.id == run_id)
        ).first()
    assert row.status == "success"
