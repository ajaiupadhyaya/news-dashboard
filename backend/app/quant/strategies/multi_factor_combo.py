"""Multi-factor combo — z-score blend of momentum, value, quality, low-vol.

Score = w_m·z(12-1 mom) + w_v·z(-P/B) + w_q·z(ROE) + w_lv·z(-σ)

Long top-decile by score, monthly rebalance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)

_DAYS_PER_MONTH = 21
_MOMENTUM_LOOKBACK_M = 12
_SKIP_M = 1
_VOL_LOOKBACK_D = 60


def _cs_z(series: pd.Series) -> pd.Series:
    mu = series.mean()
    sd = series.std()
    if sd == 0 or np.isnan(sd):
        return pd.Series(0.0, index=series.index)
    return (series - mu) / sd


class MultiFactorCombo(Strategy):
    spec = StrategySpec(
        slug="multi-factor-combo",
        name="Multi-Factor Combo",
        category="alpha",
        universe_kind="sp500",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Each month, score every S&P 500 name as a weighted z-score "
            "combination of four factors: 12-1 momentum, value (-price/"
            "book), quality (return on equity), and low-volatility "
            "(-60-day realized σ). Go long the top decile equal-weight. "
            "A classic four-factor portfolio."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "w_momentum": [0.0, 0.5, 1.0],
        "w_value":    [0.0, 0.5, 1.0],
        "w_quality":  [0.0, 0.5, 1.0],
        "w_lowvol":   [0.0, 0.5, 1.0],
        "top_pct":    [5, 10],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        if not ctx.fundamentals:
            return pd.DataFrame(0.0, index=bars.index, columns=bars.columns)

        wm = float(params["w_momentum"])
        wv = float(params["w_value"])
        wq = float(params["w_quality"])
        wlv = float(params["w_lowvol"])
        top_pct = int(params["top_pct"])

        lookback_d = _MOMENTUM_LOOKBACK_M * _DAYS_PER_MONTH
        skip_d = _SKIP_M * _DAYS_PER_MONTH
        warmup = lookback_d + skip_d
        if len(bars) < warmup:
            return pd.DataFrame(0.0, index=bars.index, columns=bars.columns)

        momentum = (bars.shift(skip_d) / bars.shift(skip_d + lookback_d)) - 1.0
        volatility = bars.pct_change().rolling(_VOL_LOOKBACK_D).std()

        pb_series = pd.Series({
            sym: ctx.fundamentals[sym].price_to_book
            for sym in bars.columns
            if sym in ctx.fundamentals and ctx.fundamentals[sym].price_to_book is not None
        })
        roe_series = pd.Series({
            sym: ctx.fundamentals[sym].roe
            for sym in bars.columns
            if sym in ctx.fundamentals and ctx.fundamentals[sym].roe is not None
        })

        weights = pd.DataFrame(0.0, index=bars.index, columns=bars.columns)
        bars_idx = pd.to_datetime(bars.index)
        month_periods = bars_idx.to_period("M")
        last_per_month = pd.Series(bars_idx, index=bars_idx).groupby(month_periods).max()
        rebal_set = set(last_per_month.values)
        winners: list[str] = []

        for i, day in enumerate(bars_idx):
            if day in rebal_set and i >= warmup:
                mom_row = momentum.iloc[i].dropna()
                vol_row = volatility.iloc[i].dropna()
                common = (
                    mom_row.index
                    .intersection(vol_row.index)
                    .intersection(pb_series.index)
                    .intersection(roe_series.index)
                )
                if len(common) == 0:
                    continue
                z_mom = _cs_z(mom_row.loc[common])
                z_val = _cs_z(-pb_series.loc[common].astype(float))
                z_qual = _cs_z(roe_series.loc[common].astype(float))
                z_lv = _cs_z(-vol_row.loc[common])
                score = wm * z_mom + wv * z_val + wq * z_qual + wlv * z_lv
                n_pick = max(1, int(len(score) * top_pct / 100))
                winners = score.sort_values(ascending=False).head(n_pick).index.tolist()
            if winners:
                w = 1.0 / len(winners)
                for sym in winners:
                    if sym in weights.columns:
                        weights.iloc[i, weights.columns.get_loc(sym)] = w
        return weights
