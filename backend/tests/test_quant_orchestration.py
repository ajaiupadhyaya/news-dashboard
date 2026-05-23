import json
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select

from app.database import (
    bar_cache, get_engine, strategies, strategy_equity,
    strategy_runs, strategy_trades,
)
from app.quant.bars import upsert_bars
from app.quant.orchestration import inception_walkforward
from app.quant.strategies.buy_hold_spy import BuyHoldSPY
from app.quant.strategies.sma_crossover import SmaCrossover


def _seed_spy_bars(years: int = 6) -> pd.DataFrame:
    import numpy as np
    idx = pd.bdate_range("2018-01-02", periods=252 * years)
    prices = pd.Series(
        100.0 * (1.0008 ** np.arange(len(idx))),
        index=idx,
    )
    df = pd.DataFrame({
        "Open": prices, "High": prices * 1.001, "Low": prices * 0.999,
        "Close": prices, "Adj Close": prices,
        "Volume": [1_000_000] * len(idx),
    })
    upsert_bars("SPY", df)
    return df


def test_inception_walkforward_buyhold_writes_run_and_equity(db):
    _seed_spy_bars(years=6)
    strategy = BuyHoldSPY()
    run_id = inception_walkforward(
        strategy,
        train_years=3, test_years=1, step_months=6,
        initial_equity=100_000,
    )
    with get_engine().begin() as conn:
        run_row = conn.execute(
            select(strategy_runs).where(strategy_runs.c.id == run_id)
        ).first()
        equity_rows = conn.execute(
            select(strategy_equity).where(
                strategy_equity.c.strategy_slug == "buy-hold-spy"
            )
        ).all()
    assert run_row.status == "success"
    assert run_row.summary_metrics is not None
    assert json.loads(run_row.walkforward_windows)
    assert len(equity_rows) > 0
    # Every equity row should be tagged backtest (forward-step doesn't run here).
    assert all(r.phase == "backtest" for r in equity_rows)


def test_inception_walkforward_sma_runs_grid_and_picks_winner(db):
    _seed_spy_bars(years=6)
    strategy = SmaCrossover()
    run_id = inception_walkforward(
        strategy,
        train_years=3, test_years=1, step_months=6,
        initial_equity=100_000,
    )
    with get_engine().begin() as conn:
        row = conn.execute(
            select(strategy_runs).where(strategy_runs.c.id == run_id)
        ).first()
        chosen = conn.execute(
            select(strategies.c.chosen_params).where(
                strategies.c.slug == "sma-crossover"
            )
        ).first()
    assert row.status == "success"
    sweep = json.loads(row.param_sweep)
    assert len(sweep) > 0
    assert chosen is not None
    chosen_params = json.loads(chosen.chosen_params)
    assert "fast" in chosen_params and "slow" in chosen_params
    assert chosen_params["fast"] < chosen_params["slow"]


def test_inception_walkforward_replaces_prior_backtest_rows(db):
    """Re-running the orchestrator wipes the strategy's backtest rows
    and rewrites them — the spec's idempotency rule for backtest phase."""
    _seed_spy_bars(years=6)
    strategy = BuyHoldSPY()
    inception_walkforward(strategy, train_years=3, test_years=1, step_months=6,
                          initial_equity=100_000)
    with get_engine().begin() as conn:
        n1 = len(conn.execute(
            select(strategy_equity).where(strategy_equity.c.strategy_slug == "buy-hold-spy")
        ).all())
    inception_walkforward(strategy, train_years=3, test_years=1, step_months=6,
                          initial_equity=100_000)
    with get_engine().begin() as conn:
        n2 = len(conn.execute(
            select(strategy_equity).where(strategy_equity.c.strategy_slug == "buy-hold-spy"
            )
        ).all())
    # Same data + same params => same row count.
    assert n1 == n2 > 0
