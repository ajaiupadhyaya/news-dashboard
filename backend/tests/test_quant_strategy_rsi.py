import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.rsi_mean_reversion import RsiMeanReversion


def test_metadata():
    s = RsiMeanReversion()
    assert s.spec.slug == "rsi-mean-reversion"
    assert s.spec.category == "classic"
    assert s.spec.universe_kind == "sp500"
    assert set(s.sweep_grid.keys()) == {"lookback", "lower", "upper"}


def test_signals_long_when_rsi_below_lower():
    s = RsiMeanReversion()
    idx = pd.date_range("2026-01-01", periods=40, freq="B")
    prices = list(range(100, 120)) + list(range(120, 100, -1))
    bars = pd.DataFrame({"AAA": [float(p) for p in prices]}, index=idx)
    w = s.generate_signals(bars, params={"lookback": 14, "lower": 30, "upper": 70},
                           ctx=StrategyContext())
    assert w["AAA"].iloc[-1] > 0


def test_signals_max_20_concurrent_positions():
    s = RsiMeanReversion()
    idx = pd.date_range("2026-01-01", periods=30, freq="B")
    data = {}
    for i in range(30):
        data[f"S{i:02d}"] = [120.0 - j * 1.0 for j in range(30)]
    bars = pd.DataFrame(data, index=idx)
    w = s.generate_signals(bars, params={"lookback": 14, "lower": 30, "upper": 70},
                           ctx=StrategyContext())
    last_row = w.iloc[-1]
    n_active = int((last_row > 0).sum())
    assert n_active <= 20
