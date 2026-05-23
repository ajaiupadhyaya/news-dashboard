"""Cross-sectional momentum — long top decile by lookback-month return.

S&P 500. Monthly rebalance on the last business day. Sweep grid:
lookback (months), skip (months — typically 1 to drop the prior month
that often shows mean reversion), top_pct (top percentile to long).
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)

_DAYS_PER_MONTH = 21


class CrossSectionalMomentum(Strategy):
    spec = StrategySpec(
        slug="cross-sectional-momentum",
        name="Cross-Sectional Momentum",
        category="classic",
        universe_kind="sp500",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Each month, rank S&P 500 names by their lookback-month total "
            "return excluding the most recent `skip` month(s), then go "
            "long the top decile equal-weight. The classic 12-1 momentum "
            "factor (Jegadeesh & Titman 1993)."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "lookback": [6, 9, 12],
        "skip": [0, 1],
        "top_pct": [5, 10, 20],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        lookback_m = int(params["lookback"])
        skip_m = int(params["skip"])
        top_pct = int(params["top_pct"])

        lookback_d = lookback_m * _DAYS_PER_MONTH
        skip_d = skip_m * _DAYS_PER_MONTH
        warmup = lookback_d + skip_d

        if len(bars) < warmup:
            return pd.DataFrame(0.0, index=bars.index, columns=bars.columns)

        # Momentum at day t = price[t-skip_d] / price[t-skip_d-lookback_d] - 1
        shifted = bars.shift(skip_d)
        base = bars.shift(skip_d + lookback_d)
        momentum = (shifted / base) - 1.0

        return _monthly_rebalance_weights(
            bars=bars, momentum=momentum, top_pct=top_pct, warmup=warmup,
        )


def _monthly_rebalance_weights(
    *, bars: pd.DataFrame, momentum: pd.DataFrame, top_pct: int, warmup: int,
) -> pd.DataFrame:
    """Reusable monthly-rebalance routine.

    Given a momentum DataFrame (date × symbol) and the warmup threshold,
    pick the top-pct% per month-end rebalance date and hold equal-weight
    until the next rebalance.
    """
    weights = pd.DataFrame(0.0, index=bars.index, columns=bars.columns)
    if len(bars) <= warmup:
        return weights
    bars_idx = pd.to_datetime(bars.index)
    month_periods = bars_idx.to_period("M")
    last_day_per_month = pd.Series(bars_idx, index=bars_idx).groupby(month_periods).max()
    rebal_days = {d for d in last_day_per_month.values if d >= bars_idx[warmup]}

    current_winners: list[str] = []
    for i, day in enumerate(bars_idx):
        if day in rebal_days:
            mrow = momentum.iloc[i].dropna()
            if not mrow.empty:
                n_pick = max(1, int(len(mrow) * top_pct / 100))
                current_winners = mrow.sort_values(ascending=False).head(n_pick).index.tolist()
        if current_winners:
            w = 1.0 / len(current_winners)
            for sym in current_winners:
                weights.iloc[i, weights.columns.get_loc(sym)] = w
    return weights
