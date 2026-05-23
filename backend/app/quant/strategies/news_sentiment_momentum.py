"""News-sentiment momentum — long names with highest weighted news score.

Score = (1 - sw) * z(rolling_coverage) + sw * z(rolling_sentiment)

Monthly rebalance. Top `top_pct`% by score equal-weight. Reads
ctx._news_signal (a dict with 'coverage' and 'sentiment' DataFrames)
populated by the orchestrator.
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)


class NewsSentimentMomentum(Strategy):
    spec = StrategySpec(
        slug="news-sentiment-momentum",
        name="News-Sentiment Momentum",
        category="alpha",
        universe_kind="news-top100",
        inception_date="2026-05-22",
        live_start_date="2026-05-22",
        methodology_blurb=(
            "Each month, rank S&P 500 names by a weighted combination of "
            "rolling news-cluster volume (attention) and average news "
            "sentiment. Long the top decile equal-weight. Uses the news "
            "domain's own ingestion pipeline — the data that powers the "
            "dashboard's Top Stories panel."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "sentiment_weight": [0.3, 0.5, 0.7],
        "lookback_days": [3, 7, 14],
        "top_pct": [5, 10, 20],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        sw = float(params["sentiment_weight"])
        lookback = int(params["lookback_days"])
        top_pct = int(params["top_pct"])

        news_signal = getattr(ctx, "_news_signal", None)
        if not news_signal:
            return pd.DataFrame(0.0, index=bars.index, columns=bars.columns)

        cov = news_signal["coverage"].copy()
        sent = news_signal["sentiment"].copy()
        cov.index = pd.to_datetime(cov.index)
        sent.index = pd.to_datetime(sent.index)
        bars_idx = pd.to_datetime(bars.index)

        cov_aligned = cov.reindex(bars_idx).reindex(columns=bars.columns).fillna(0)
        sent_aligned = sent.reindex(bars_idx).reindex(columns=bars.columns).fillna(0)

        roll_cov = cov_aligned.rolling(lookback, min_periods=1).sum()
        roll_sent = sent_aligned.rolling(lookback, min_periods=1).mean()

        def _z(df: pd.DataFrame) -> pd.DataFrame:
            mu = df.mean(axis=1)
            sd = df.std(axis=1).replace(0, 1.0)
            return df.sub(mu, axis=0).div(sd, axis=0)

        score = (1 - sw) * _z(roll_cov) + sw * _z(roll_sent)

        month_periods = bars_idx.to_period("M")
        last_per_month = pd.Series(bars_idx, index=bars_idx).groupby(month_periods).max()
        rebal_set = set(last_per_month.values)

        weights = pd.DataFrame(0.0, index=bars.index, columns=bars.columns)
        winners: list[str] = []
        for i, day in enumerate(bars_idx):
            if day in rebal_set:
                row = score.iloc[i].dropna()
                if not row.empty:
                    n_pick = max(1, int(len(row) * top_pct / 100))
                    winners = row.sort_values(ascending=False).head(n_pick).index.tolist()
            if winners:
                w = 1.0 / len(winners)
                for sym in winners:
                    weights.iloc[i, weights.columns.get_loc(sym)] = w
        return weights
