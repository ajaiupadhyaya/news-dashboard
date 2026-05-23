"""SMA crossover — long when fast-SMA > slow-SMA, flat otherwise.

Trades a single symbol (SPY). The classic trend-following baseline.
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)


class SmaCrossover(Strategy):
    spec = StrategySpec(
        slug="sma-crossover",
        name="SMA Crossover",
        category="classic",
        universe_kind="spy",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Long the SPDR S&P 500 ETF (SPY) when the fast simple moving "
            "average crosses above the slow simple moving average; flat "
            "otherwise. A canonical trend-following baseline strategy."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "fast": [10, 20, 50],
        "slow": [50, 100, 200],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        fast = int(params["fast"])
        slow = int(params["slow"])
        spy = bars["SPY"]
        fast_sma = spy.rolling(fast, min_periods=fast).mean()
        slow_sma = spy.rolling(slow, min_periods=slow).mean()
        long = (fast_sma > slow_sma).astype(float)
        long = long.fillna(0.0)
        return pd.DataFrame({"SPY": long}, index=bars.index)
