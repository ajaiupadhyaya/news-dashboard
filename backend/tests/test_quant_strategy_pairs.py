import numpy as np
import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.pairs_trading import PairsTrading


def _make_bars(n: int) -> pd.DataFrame:
    """Build a synthetic 10-symbol bar DataFrame where KO diverges
    from PEP via a regime shift so the KO/PEP spread z-score breaches
    the entry threshold.  Fully deterministic — no random seed required.

    Design:
    - Bars 0-99: KO and PEP co-move along the same log-price trend with
      a small sine oscillation, giving a near-zero, stationary spread.
    - Bar 100 onward: KO log-price drops by 0.4 (sudden underperformance).
      The rolling window mean still reflects the pre-shift level, so the
      z-score falls well below −2.0 and the strategy enters position +1
      (long KO, short PEP) — which persists to the end.
    """
    idx = pd.bdate_range("2026-01-01", periods=n)
    t = np.arange(n)
    pep_log = np.log(150.0) + 0.0005 * t + 0.008 * np.sin(t * 2.0 * np.pi / 30.0)
    ko_log = np.log(50.0) + 0.0005 * t + 0.008 * np.sin(t * 2.0 * np.pi / 30.0)
    if n > 100:
        ko_log[100:] -= 0.4   # regime shift — KO suddenly underperforms
    return pd.DataFrame({
        "KO": np.exp(ko_log),
        "PEP": np.exp(pep_log),
        "MA": [400.0] * n,
        "V": [240.0] * n,
        "GOOG": [140.0] * n,
        "META": [500.0] * n,
        "XOM": [100.0] * n,
        "CVX": [150.0] * n,
        "JPM": [150.0] * n,
        "BAC": [30.0] * n,
    }, index=idx)


def test_metadata():
    s = PairsTrading()
    assert s.spec.slug == "pairs-trading"
    assert s.spec.category == "classic"
    assert s.spec.universe_kind == "pairs-fixed"
    assert s.spec.allow_short is True
    assert set(s.sweep_grid.keys()) == {"lookback", "entry_z", "exit_z"}


def test_signals_emit_offsetting_long_short_legs():
    """With a stretched spread, the strategy must take *both* sides."""
    s = PairsTrading()
    bars = _make_bars(200)
    w = s.generate_signals(bars, params={"lookback": 60, "entry_z": 2.0, "exit_z": 0.5},
                           ctx=StrategyContext())
    last = w.iloc[-1]
    assert last["KO"] > 0
    assert last["PEP"] < 0
    assert abs(abs(last["KO"]) - abs(last["PEP"])) < 0.05


def test_zero_below_lookback():
    s = PairsTrading()
    bars = _make_bars(20)
    w = s.generate_signals(bars, params={"lookback": 60, "entry_z": 2.0, "exit_z": 0.5},
                           ctx=StrategyContext())
    assert (w.values == 0).all()
