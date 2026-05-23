import numpy as np
import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.cross_sectional_momentum import CrossSectionalMomentum


def test_metadata():
    s = CrossSectionalMomentum()
    assert s.spec.slug == "cross-sectional-momentum"
    assert s.spec.category == "classic"
    assert s.spec.universe_kind == "sp500"
    assert set(s.sweep_grid.keys()) == {"lookback", "skip", "top_pct"}


def test_picks_top_decile_each_month():
    s = CrossSectionalMomentum()
    idx = pd.bdate_range("2024-01-02", periods=300)
    data = {}
    for i in range(20):
        data[f"S{i:02d}"] = 100.0 * (1 + 0.0001 * i) ** np.arange(len(idx))
    bars = pd.DataFrame(data, index=idx)
    w = s.generate_signals(bars, params={"lookback": 9, "skip": 1, "top_pct": 10},
                           ctx=StrategyContext())
    last = w.iloc[-1]
    assert (last["S19"] > 0) and (last["S18"] > 0)
    assert last["S00"] == 0


def test_zero_until_lookback_plus_skip_months_elapsed():
    s = CrossSectionalMomentum()
    idx = pd.bdate_range("2024-01-02", periods=120)
    data = {f"S{i:02d}": [100.0 + i] * len(idx) for i in range(10)}
    bars = pd.DataFrame(data, index=idx)
    w = s.generate_signals(bars, params={"lookback": 9, "skip": 1, "top_pct": 10},
                           ctx=StrategyContext())
    assert (w.values == 0).all()
