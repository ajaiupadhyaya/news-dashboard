import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.buy_hold_spy import BuyHoldSPY


def test_metadata():
    s = BuyHoldSPY()
    assert s.spec.slug == "buy-hold-spy"
    assert s.spec.category == "benchmark"
    assert s.spec.universe_kind == "spy"
    assert s.sweep_grid == {}


def test_generate_signals_returns_full_long_weight():
    s = BuyHoldSPY()
    bars = pd.DataFrame(
        {"SPY": [100.0, 101.0, 102.0]},
        index=pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-04"]),
    )
    weights = s.generate_signals(bars, params={}, ctx=StrategyContext())
    assert list(weights.columns) == ["SPY"]
    assert (weights["SPY"] == 1.0).all()


def test_generate_signals_skips_leading_nan():
    s = BuyHoldSPY()
    bars = pd.DataFrame(
        {"SPY": [float("nan"), 100.0, 101.0]},
        index=pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-04"]),
    )
    weights = s.generate_signals(bars, params={}, ctx=StrategyContext())
    assert weights["SPY"].iloc[0] == 0.0
    assert (weights["SPY"].iloc[1:] == 1.0).all()
