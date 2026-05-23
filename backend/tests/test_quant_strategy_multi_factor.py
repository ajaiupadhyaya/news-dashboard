import numpy as np
import pandas as pd

from app.quant.fundamentals import Fundamentals
from app.quant.strategies.base import StrategyContext
from app.quant.strategies.multi_factor_combo import MultiFactorCombo


def test_metadata():
    s = MultiFactorCombo()
    assert s.spec.slug == "multi-factor-combo"
    assert s.spec.category == "alpha"
    assert s.spec.universe_kind == "sp500"
    grid = s.sweep_grid
    assert {"w_momentum", "w_value", "w_quality", "w_lowvol", "top_pct"} == set(grid.keys())


def test_uses_fundamentals_from_ctx():
    s = MultiFactorCombo()
    idx = pd.bdate_range("2024-01-02", periods=300)
    data = {f"S{i:02d}": 100.0 * (1 + 0.0001 * i) ** np.arange(len(idx)) for i in range(20)}
    bars = pd.DataFrame(data, index=idx)
    ctx = StrategyContext()
    ctx.fundamentals = {
        sym: Fundamentals(symbol=sym, price_to_book=20.0 - i, roe=0.01 * i)
        for i, sym in enumerate(bars.columns)
    }
    w = s.generate_signals(
        bars, params={"w_momentum": 1.0, "w_value": 1.0, "w_quality": 1.0, "w_lowvol": 1.0,
                       "top_pct": 10},
        ctx=ctx,
    )
    assert w.iloc[-1]["S19"] > 0


def test_zero_when_fundamentals_missing():
    s = MultiFactorCombo()
    idx = pd.bdate_range("2024-01-02", periods=300)
    bars = pd.DataFrame({"AAA": [100.0] * len(idx)}, index=idx)
    ctx = StrategyContext()
    ctx.fundamentals = {}
    w = s.generate_signals(
        bars, params={"w_momentum": 1.0, "w_value": 1.0, "w_quality": 1.0, "w_lowvol": 1.0,
                       "top_pct": 10},
        ctx=ctx,
    )
    assert (w.values == 0).all()
