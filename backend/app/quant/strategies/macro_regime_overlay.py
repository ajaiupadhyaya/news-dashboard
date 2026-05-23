"""Macro-regime overlay — momentum sized down in risk-off regimes.

Wraps the same cross-sectional momentum signal as CrossSectionalMomentum,
but reads a per-day regime label from ctx._regime (Series of date→str)
and halves gross exposure (or rotates to defensives) when risk_off.
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)
from app.quant.strategies.cross_sectional_momentum import CrossSectionalMomentum

_DEFENSIVES = ("XLP", "XLU", "XLV")


class MacroRegimeOverlay(Strategy):
    spec = StrategySpec(
        slug="macro-regime-overlay",
        name="Macro-Regime Overlay (Momentum)",
        category="alpha",
        universe_kind="sp500",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Same Jegadeesh-Titman 12-1 momentum top-decile selection as "
            "the classic cross-sectional momentum strategy, but with a "
            "FRED-derived macro regime overlay. When the yield curve "
            "inverts and unemployment is rising (risk_off), the strategy "
            "halves gross exposure — and optionally rotates the residual "
            "into defensive sectors (XLP/XLU/XLV) — to dampen drawdowns "
            "during recessionary regimes."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "lookback": [6, 9, 12],
        "skip": [0, 1],
        "top_pct": [5, 10],
        "defensive_rotation": [False, True],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        base_params = {
            "lookback": params["lookback"],
            "skip": params["skip"],
            "top_pct": params["top_pct"],
        }
        base = CrossSectionalMomentum().generate_signals(bars, base_params, ctx)

        regime = getattr(ctx, "_regime", None)
        if regime is None:
            return base

        defensive = bool(params.get("defensive_rotation", False))

        idx_dates = pd.to_datetime(bars.index).strftime("%Y-%m-%d")
        regime_aligned = regime.reindex(idx_dates).fillna("risk_on")

        out = base.copy()
        for i in range(len(idx_dates)):
            if regime_aligned.iloc[i] == "risk_off":
                out.iloc[i] = out.iloc[i] * 0.5
                if defensive:
                    available_def = [d for d in _DEFENSIVES if d in out.columns]
                    if available_def:
                        per = 0.5 / len(available_def)
                        for d in available_def:
                            out.iloc[i, out.columns.get_loc(d)] = per
        return out
