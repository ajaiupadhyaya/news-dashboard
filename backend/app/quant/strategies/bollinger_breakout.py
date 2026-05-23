"""Bollinger breakout — long when close > upper band, exit on cross-below middle band.

Trades a single symbol (SPY). Volatility-breakout classic.
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)


class BollingerBreakout(Strategy):
    spec = StrategySpec(
        slug="bollinger-breakout",
        name="Bollinger Breakout",
        category="classic",
        universe_kind="spy",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Go long the SPDR S&P 500 ETF (SPY) on a close above the upper "
            "Bollinger band; exit when the close drops back below the "
            "middle (moving-average) band. Captures momentum breakouts "
            "out of low-volatility regimes."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "lookback": [10, 20, 30],
        "std": [1.5, 2.0, 2.5],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        lookback = int(params["lookback"])
        std_mult = float(params["std"])
        spy = bars["SPY"]
        mid = spy.rolling(lookback, min_periods=lookback).mean()
        sd = spy.rolling(lookback, min_periods=lookback).std()
        upper = mid + std_mult * sd

        long = pd.Series(0.0, index=spy.index)
        holding = False
        for i in range(len(spy)):
            if pd.isna(upper.iloc[i]) or pd.isna(mid.iloc[i]):
                continue
            if not holding and spy.iloc[i] > upper.iloc[i]:
                holding = True
            elif holding and spy.iloc[i] < mid.iloc[i]:
                holding = False
            long.iloc[i] = 1.0 if holding else 0.0
        return pd.DataFrame({"SPY": long}, index=bars.index)
