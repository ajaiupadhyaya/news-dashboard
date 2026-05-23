import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.news_sentiment_momentum import NewsSentimentMomentum


def test_metadata():
    s = NewsSentimentMomentum()
    assert s.spec.slug == "news-sentiment-momentum"
    assert s.spec.category == "alpha"
    assert s.spec.universe_kind == "news-top100"
    assert set(s.sweep_grid.keys()) == {"sentiment_weight", "lookback_days", "top_pct"}


def test_picks_top_by_combined_score():
    s = NewsSentimentMomentum()
    idx = pd.bdate_range("2026-01-02", periods=80)
    bars = pd.DataFrame({
        "AAA": 100.0, "BBB": 100.0, "CCC": 100.0, "DDD": 100.0, "EEE": 100.0,
    }, index=idx)
    cov_dates = pd.date_range("2026-01-02", periods=80, freq="D").strftime("%Y-%m-%d")
    coverage = pd.DataFrame(0, index=cov_dates, columns=["AAA", "BBB", "CCC", "DDD", "EEE"])
    coverage["AAA"] = 5
    coverage["BBB"] = 1
    sentiment = pd.DataFrame(0.0, index=cov_dates, columns=["AAA", "BBB", "CCC", "DDD", "EEE"])
    sentiment["AAA"] = 0.7
    sentiment["BBB"] = 0.3
    ctx = StrategyContext()
    setattr(ctx, "_news_signal", {"coverage": coverage, "sentiment": sentiment})
    w = s.generate_signals(
        bars, params={"sentiment_weight": 0.5, "lookback_days": 7, "top_pct": 20},
        ctx=ctx,
    )
    last = w.iloc[-1]
    assert last["AAA"] > 0
    assert last["CCC"] == 0


def test_zero_when_no_news_signal_in_ctx():
    s = NewsSentimentMomentum()
    idx = pd.bdate_range("2026-01-02", periods=80)
    bars = pd.DataFrame({"AAA": [100.0] * 80, "BBB": [100.0] * 80}, index=idx)
    ctx = StrategyContext()
    w = s.generate_signals(
        bars, params={"sentiment_weight": 0.5, "lookback_days": 7, "top_pct": 50},
        ctx=ctx,
    )
    assert (w.values == 0).all()
