import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.bollinger_breakout import BollingerBreakout


def test_metadata():
    s = BollingerBreakout()
    assert s.spec.slug == "bollinger-breakout"
    assert s.spec.category == "classic"
    assert s.spec.universe_kind == "spy"
    assert set(s.sweep_grid.keys()) == {"lookback", "std"}


def test_generate_signals_long_on_upper_band_breakout():
    s = BollingerBreakout()
    base = [100.0] * 30 + [102.0] * 10 + [110.0] * 20
    idx = pd.date_range("2026-01-01", periods=len(base), freq="B")
    bars = pd.DataFrame({"SPY": base}, index=idx)
    w = s.generate_signals(bars, params={"lookback": 20, "std": 2.0}, ctx=StrategyContext())
    assert w["SPY"].iloc[-1] == 1.0


def test_generate_signals_flat_below_middle_band():
    s = BollingerBreakout()
    base = [100.0 + (0.5 if i % 2 else -0.5) for i in range(60)]
    idx = pd.date_range("2026-01-01", periods=len(base), freq="B")
    bars = pd.DataFrame({"SPY": base}, index=idx)
    w = s.generate_signals(bars, params={"lookback": 20, "std": 2.0}, ctx=StrategyContext())
    assert (w["SPY"].iloc[20:] == 0.0).all()


def test_generate_signals_zero_before_lookback_filled():
    s = BollingerBreakout()
    idx = pd.date_range("2026-01-01", periods=30, freq="B")
    bars = pd.DataFrame({"SPY": [100.0] * 30}, index=idx)
    w = s.generate_signals(bars, params={"lookback": 20, "std": 2.0}, ctx=StrategyContext())
    assert (w["SPY"].iloc[:19] == 0.0).all()
