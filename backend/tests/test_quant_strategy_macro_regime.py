import numpy as np
import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.macro_regime_overlay import MacroRegimeOverlay


def test_metadata():
    s = MacroRegimeOverlay()
    assert s.spec.slug == "macro-regime-overlay"
    assert s.spec.category == "alpha"
    assert s.spec.universe_kind == "sp500"
    assert set(s.sweep_grid.keys()) == {"lookback", "skip", "top_pct", "defensive_rotation"}


def test_halves_exposure_in_risk_off():
    s = MacroRegimeOverlay()
    idx = pd.bdate_range("2024-01-02", periods=300)
    data = {f"S{i:02d}": 100.0 * (1 + 0.0001 * i) ** np.arange(len(idx)) for i in range(20)}
    bars = pd.DataFrame(data, index=idx)
    regime = pd.Series("risk_on", index=idx.strftime("%Y-%m-%d"))
    regime.iloc[-60:] = "risk_off"
    ctx = StrategyContext()
    setattr(ctx, "_regime", regime)
    w_risk_off = s.generate_signals(
        bars, params={"lookback": 9, "skip": 1, "top_pct": 10, "defensive_rotation": False},
        ctx=ctx,
    )
    gross = w_risk_off.iloc[-1].abs().sum()
    assert 0.3 < gross < 0.6


def test_no_regime_in_ctx_falls_back_to_base_momentum():
    s = MacroRegimeOverlay()
    idx = pd.bdate_range("2024-01-02", periods=300)
    data = {f"S{i:02d}": 100.0 * (1 + 0.0001 * i) ** np.arange(len(idx)) for i in range(20)}
    bars = pd.DataFrame(data, index=idx)
    ctx = StrategyContext()  # no _regime
    w = s.generate_signals(
        bars, params={"lookback": 9, "skip": 1, "top_pct": 10, "defensive_rotation": False},
        ctx=ctx,
    )
    # Should match base momentum (gross ~= 1.0 at the end).
    gross = w.iloc[-1].abs().sum()
    assert 0.9 < gross < 1.1
