"""Pairs trading — market-neutral long/short on cointegrated pairs.

Five fixed pairs from app.quant.universe.PAIRS. For each pair (A, B),
compute a rolling-OLS hedge ratio β from log(A) ~ β·log(B), then the
spread = log(A) - β·log(B). Z-score the spread by its rolling mean/std.
Long A, short B when z < -entry. Short A, long B when z > +entry.
Flat when |z| < exit. Equal capital allocation across the 5 pairs.

Engine note: negative weights flow through _portfolio_from_weights
unchanged; vectorbt's from_orders with size_type="targetpercent" natively
accepts negative target fractions as short positions. No engine changes
were required.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)
from app.quant.universe import PAIRS


def _rolling_beta(log_a: pd.Series, log_b: pd.Series, lookback: int) -> pd.Series:
    """Rolling OLS slope of log_a on log_b."""
    cov = log_a.rolling(lookback).cov(log_b)
    var = log_b.rolling(lookback).var()
    return cov / var.replace(0, np.nan)


class PairsTrading(Strategy):
    spec = StrategySpec(
        slug="pairs-trading",
        name="Pairs Trading",
        category="classic",
        universe_kind="pairs-fixed",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Trades five cointegrated equity pairs (KO/PEP, MA/V, "
            "GOOG/META, XOM/CVX, JPM/BAC). For each pair, the spread "
            "log(A) – β·log(B) is z-scored over a rolling window. When |z| "
            "exceeds the entry threshold the strategy goes long the "
            "underperformer and short the outperformer; positions close "
            "when |z| reverts inside the exit band. Market-neutral by "
            "construction — the only strategy in this lab that shorts."
        ),
        allow_short=True,
    )
    sweep_grid: ParamGrid = {
        "lookback": [30, 60, 90],
        "entry_z": [1.5, 2.0, 2.5],
        "exit_z": [0.0, 0.5],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        lookback = int(params["lookback"])
        entry_z = float(params["entry_z"])
        exit_z = float(params["exit_z"])

        legs_per_pair = 1.0 / len(PAIRS)
        weights = pd.DataFrame(0.0, index=bars.index, columns=bars.columns)

        for (a, b) in PAIRS:
            if a not in bars.columns or b not in bars.columns:
                continue
            log_a = np.log(bars[a].replace(0, np.nan))
            log_b = np.log(bars[b].replace(0, np.nan))
            beta = _rolling_beta(log_a, log_b, lookback)
            spread = log_a - beta * log_b
            mu = spread.rolling(lookback).mean()
            sd = spread.rolling(lookback).std()
            z = (spread - mu) / sd.replace(0, np.nan)

            position = 0   # +1 = long A short B; -1 = short A long B; 0 = flat
            for i in range(len(bars.index)):
                zi = z.iloc[i]
                if pd.isna(zi):
                    continue
                if position == 0:
                    if zi < -entry_z:
                        position = 1
                    elif zi > entry_z:
                        position = -1
                else:
                    if abs(zi) < exit_z:
                        position = 0

                if position == 1:
                    weights.iloc[i, weights.columns.get_loc(a)] = legs_per_pair
                    weights.iloc[i, weights.columns.get_loc(b)] = -legs_per_pair
                elif position == -1:
                    weights.iloc[i, weights.columns.get_loc(a)] = -legs_per_pair
                    weights.iloc[i, weights.columns.get_loc(b)] = legs_per_pair
        return weights
