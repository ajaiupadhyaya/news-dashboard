"""Buy & Hold SPY — benchmark for every other strategy."""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)


class BuyHoldSPY(Strategy):
    spec = StrategySpec(
        slug="buy-hold-spy",
        name="Buy & Hold SPY",
        category="benchmark",
        universe_kind="spy",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Always long the SPDR S&P 500 ETF (SPY) at 100% weight. "
            "Serves as the passive benchmark every active strategy is "
            "compared against."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {}

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        # Weight = 1 on every day SPY has a non-NaN price; 0 before that.
        spy = bars["SPY"]
        w = (spy.notna()).astype(float)
        return pd.DataFrame({"SPY": w}, index=bars.index)
