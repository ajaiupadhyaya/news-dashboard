import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.sma_crossover import SmaCrossover


def test_metadata():
    s = SmaCrossover()
    assert s.spec.slug == "sma-crossover"
    assert s.spec.category == "classic"
    assert s.spec.universe_kind == "spy"
    # Grid has fast / slow with fast < slow constraint applied at sweep time.
    assert set(s.sweep_grid.keys()) == {"fast", "slow"}


def test_generate_signals_long_when_fast_above_slow():
    s = SmaCrossover()
    # Construct a series that rises then falls: fast SMA crosses above slow then below.
    idx = pd.date_range("2026-01-01", periods=60, freq="B")
    prices = pd.Series(
        # Linearly rising 30 days, then linearly falling 30 days.
        list(range(100, 130)) + list(range(130, 100, -1)),
        index=idx,
    )
    bars = pd.DataFrame({"SPY": prices.astype(float)})
    weights = s.generate_signals(bars, params={"fast": 5, "slow": 20}, ctx=StrategyContext())
    # On the rising leg, the fast SMA should eventually exceed the slow SMA,
    # producing weight=1; on the falling leg, weight returns to 0.
    rising_late = weights["SPY"].iloc[24]   # late in the rising leg
    falling_late = weights["SPY"].iloc[55]
    assert rising_late == 1.0
    assert falling_late == 0.0


def test_generate_signals_zero_before_slow_window_filled():
    s = SmaCrossover()
    idx = pd.date_range("2026-01-01", periods=30, freq="B")
    prices = pd.Series(range(100, 130), index=idx).astype(float)
    bars = pd.DataFrame({"SPY": prices})
    weights = s.generate_signals(bars, params={"fast": 5, "slow": 20}, ctx=StrategyContext())
    # First (slow-1) rows must be 0 because the slow SMA is undefined.
    assert (weights["SPY"].iloc[:19] == 0.0).all()
