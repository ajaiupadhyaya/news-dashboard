import json
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd
from sqlalchemy import insert, select

from app.database import (
    bar_cache, get_engine, strategies, strategy_runs,
)
from app.quant.bars import upsert_bars
from app.quant.jobs import (
    forward_step_all_strategies, run_inception_walkforward_async, warm_quant_bars,
)


def test_warm_quant_bars_fetches_for_enabled_universe(db):
    with get_engine().begin() as conn:
        conn.execute(insert(strategies).values(
            slug="buy-hold-spy", name="x", category="benchmark",
            methodology_blurb="x", universe_kind="spy",
            inception_date="2024-01-02", live_start_date="2025-01-02",
            chosen_params="{}",
            cost_model='{"commission":0,"slippage_bps":5,"allow_short":false}',
            enabled=1, last_forward_step_date=None,
        ))
    with patch("app.quant.jobs.fetch_and_cache") as mocked:
        mocked.return_value = 100
        warm_quant_bars(target_date="2025-06-15")
        args, kwargs = mocked.call_args
        symbols = kwargs.get("symbols") or args[0]
        assert "SPY" in symbols


def test_forward_step_all_strategies_uses_today_default(db):
    # No strategies seeded — should be no-op.
    summary = forward_step_all_strategies()
    assert isinstance(summary, dict)


def test_run_inception_walkforward_async_succeeds(db):
    """Smoke: the wrapper invokes the orchestrator and persists a run."""
    idx = pd.bdate_range("2018-01-02", periods=252 * 5)
    df = pd.DataFrame({
        "Open": 100.0, "High": 101.0, "Low": 99.0,
        "Close": 100.0, "Adj Close": 100.0, "Volume": 1_000_000,
    }, index=idx)
    upsert_bars("SPY", df)
    run_id = run_inception_walkforward_async("buy-hold-spy")
    with get_engine().begin() as conn:
        row = conn.execute(
            select(strategy_runs).where(strategy_runs.c.id == run_id)
        ).first()
    assert row.status == "success"
