"""RSI mean reversion — long when RSI < lower, exit when RSI > upper.

S&P 500 universe, per-name. Caps concurrent positions at 20 by selecting
the names with the lowest current RSI (most oversold). Equal-weight
across active positions.
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)

_MAX_CONCURRENT = 20


def _rsi(prices: pd.Series, lookback: int) -> pd.Series:
    """Wilder's RSI."""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / lookback, adjust=False, min_periods=lookback).mean()
    avg_loss = loss.ewm(alpha=1 / lookback, adjust=False, min_periods=lookback).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


class RsiMeanReversion(Strategy):
    spec = StrategySpec(
        slug="rsi-mean-reversion",
        name="RSI Mean Reversion",
        category="classic",
        universe_kind="sp500",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Go long an S&P 500 name when its Wilder RSI drops below the "
            "lower threshold (oversold), exit when RSI crosses back above "
            "the upper threshold. Caps the book at 20 concurrent positions "
            "by selecting the most-oversold names when more signals fire."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "lookback": [7, 14, 21],
        "lower": [20, 25, 30],
        "upper": [55, 65, 75],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        lookback = int(params["lookback"])
        lower = float(params["lower"])
        upper = float(params["upper"])

        rsi = bars.apply(lambda col: _rsi(col, lookback))

        holdings = pd.DataFrame(0.0, index=bars.index, columns=bars.columns)
        active: dict[str, bool] = {c: False for c in bars.columns}
        for t in range(len(bars.index)):
            row_rsi = rsi.iloc[t]
            for sym in bars.columns:
                r = row_rsi[sym]
                if pd.isna(r):
                    continue
                if not active[sym] and r < lower:
                    active[sym] = True
                elif active[sym] and r > upper:
                    active[sym] = False

            active_syms = [s for s, on in active.items() if on]
            if len(active_syms) > _MAX_CONCURRENT:
                ranked = row_rsi[active_syms].sort_values().index.tolist()
                active_syms = ranked[:_MAX_CONCURRENT]

            if active_syms:
                w = 1.0 / len(active_syms)
                for sym in active_syms:
                    holdings.iloc[t, holdings.columns.get_loc(sym)] = w
        return holdings
