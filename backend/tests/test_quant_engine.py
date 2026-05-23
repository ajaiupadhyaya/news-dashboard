import numpy as np
import pandas as pd

from app.quant.cost_model import CostModel
from app.quant.engine import EngineResult, run_single
from app.quant.strategies.base import StrategyContext
from app.quant.strategies.buy_hold_spy import BuyHoldSPY


def _spy_series(n: int = 100, start_price: float = 100.0, drift: float = 0.001):
    """Deterministic synthetic SPY price series — geometric drift, no noise."""
    idx = pd.date_range("2026-01-02", periods=n, freq="B")
    prices = start_price * (1 + drift) ** np.arange(n)
    return pd.DataFrame({"SPY": prices.astype(float)}, index=idx)


def test_run_single_buy_hold_grows_with_drift():
    bars = _spy_series(n=100, drift=0.001)
    res: EngineResult = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    # Buy & hold with zero costs ≈ SPY total return
    expected_growth = bars["SPY"].iloc[-1] / bars["SPY"].iloc[0]
    actual_growth = res.equity.iloc[-1] / 100_000
    assert abs(actual_growth - expected_growth) / expected_growth < 0.01


def test_run_single_returns_equity_indexed_by_date():
    bars = _spy_series(n=50)
    res = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    assert isinstance(res.equity, pd.Series)
    assert isinstance(res.equity.index, pd.DatetimeIndex)
    assert len(res.equity) == 50


def test_run_single_records_trades():
    bars = _spy_series(n=50)
    res = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    # Buy & hold should record at least 1 entry trade.
    assert len(res.trades) >= 1
    assert res.trades.iloc[0]["side"] in ("buy",)


def test_run_single_metrics_include_sharpe_and_max_drawdown():
    bars = _spy_series(n=252, drift=0.0008)
    res = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    assert "sharpe" in res.metrics
    assert "max_drawdown" in res.metrics
    assert "total_return" in res.metrics
    assert res.metrics["total_return"] > 0


def test_run_single_applies_slippage():
    bars = _spy_series(n=50)
    res_zero = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    res_slip = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=50),  # 50 bps
        initial_equity=100_000,
    )
    # With slippage, final equity must be strictly less.
    assert res_slip.equity.iloc[-1] < res_zero.equity.iloc[-1]


def test_run_grid_returns_one_row_per_valid_combo():
    from app.quant.engine import run_grid
    from app.quant.strategies.sma_crossover import SmaCrossover

    bars = _spy_series(n=300, drift=0.0008)
    sma = SmaCrossover()
    df = run_grid(
        sma, bars, grid=sma.sweep_grid,
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
        constraint=lambda p: p["fast"] < p["slow"],
    )
    # SMA grid: fast ∈ {10,20,50}, slow ∈ {50,100,200}; with fast<slow constraint:
    # exclude (50,50) → 8 valid combos.
    assert len(df) == 8
    assert {"fast", "slow"}.issubset(df.columns)
    assert "sharpe" in df.columns
    assert "total_return" in df.columns


def test_run_grid_without_constraint_runs_all_combos():
    from app.quant.engine import run_grid
    grid = {"a": [1, 2], "b": [10, 20, 30]}
    # Use BuyHoldSPY but pass an ignored grid — it doesn't read params.
    bars = _spy_series(n=50)
    df = run_grid(
        BuyHoldSPY(), bars, grid=grid,
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    assert len(df) == 6  # 2 × 3
