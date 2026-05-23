import json

import pandas as pd
from sqlalchemy import insert

from app.database import (
    bar_cache, get_engine, strategies, strategy_equity, strategy_trades,
)
from app.services.quant_service import build_overview


def _seed_strategy_with_equity(db, slug: str, equity_pairs: list[tuple[str, float]]):
    with get_engine().begin() as conn:
        conn.execute(insert(strategies).values(
            slug=slug, name=slug.replace("-", " ").title(),
            category="benchmark", methodology_blurb="x",
            universe_kind="spy",
            inception_date="2024-01-02", live_start_date="2025-01-02",
            chosen_params="{}",
            cost_model='{"commission":0,"slippage_bps":5,"allow_short":false}',
            enabled=1, last_forward_step_date=equity_pairs[-1][0],
        ))
        prev = None
        for d, eq in equity_pairs:
            daily_return = 0.0 if prev is None else (eq / prev - 1.0)
            conn.execute(insert(strategy_equity).values(
                strategy_slug=slug, date=d, equity=eq, cash=0.0,
                gross_exposure=eq, net_exposure=eq,
                daily_return=daily_return, phase="forward",
            ))
            prev = eq


def test_build_overview_returns_leaderboard(db):
    _seed_strategy_with_equity(db, "buy-hold-spy",
                                [("2025-01-02", 100_000),
                                 ("2025-01-03", 101_000),
                                 ("2025-01-04", 102_000)])
    payload = build_overview()
    assert "leaderboard" in payload
    assert isinstance(payload["leaderboard"], list)
    row = payload["leaderboard"][0]
    assert row["slug"] == "buy-hold-spy"
    assert row["total_return"] > 0
    assert "sharpe" in row
    assert "live_since" in row


def test_build_overview_combined_equity_series(db):
    _seed_strategy_with_equity(db, "buy-hold-spy",
                                [("2025-01-02", 100_000), ("2025-01-03", 102_000)])
    _seed_strategy_with_equity(db, "sma-crossover",
                                [("2025-01-02", 100_000), ("2025-01-03", 99_000)])
    payload = build_overview()
    series = payload["hero_equity"]
    assert isinstance(series, list)
    # Combined equity = average of normalized series; on 2025-01-02 both started at 100_000.
    assert series[0]["equity"] == 100_000
    # 2025-01-03: one up 2%, other down 1% → 100_500 mean.
    assert abs(series[1]["equity"] - 100_500) < 1


def test_build_overview_recent_trades(db):
    _seed_strategy_with_equity(db, "buy-hold-spy",
                                [("2025-01-02", 100_000)])
    with get_engine().begin() as conn:
        conn.execute(insert(strategy_trades).values(
            strategy_slug="buy-hold-spy", date="2025-01-02", symbol="SPY",
            side="buy", qty=210, price=470.5, commission=0.0,
            notional=98_805.0, phase="forward",
        ))
    payload = build_overview()
    trades = payload["recent_trades"]
    assert len(trades) == 1
    assert trades[0]["symbol"] == "SPY"


def test_build_strategy_detail_returns_full_payload(db):
    _seed_strategy_with_equity(db, "buy-hold-spy",
                                [(f"2025-01-{i:02d}", 100_000 * (1 + 0.001 * i))
                                 for i in range(2, 32)])
    # Also insert a strategy_runs row with summary metrics + windows + sweep.
    from app.database import strategy_runs
    with get_engine().begin() as conn:
        conn.execute(insert(strategy_runs).values(
            strategy_slug="buy-hold-spy",
            run_kind="inception-walkforward",
            started_at="2025-05-22T00:00:00Z",
            finished_at="2025-05-22T00:05:00Z",
            status="success",
            progress=json.dumps({"windows_done": 2, "windows_total": 2}),
            summary_metrics=json.dumps({"total_return": 0.5, "sharpe": 1.0,
                                         "max_drawdown": -0.1}),
            walkforward_windows=json.dumps([
                {"train_start": "2018-01-02", "train_end": "2020-12-31",
                 "test_start": "2021-01-02", "test_end": "2021-12-31",
                 "chosen_params": {}, "oos_metrics": {"sharpe": 1.0}},
            ]),
            param_sweep=json.dumps([]),
        ))
    from app.services.quant_service import build_strategy_detail
    detail = build_strategy_detail("buy-hold-spy")
    assert detail["slug"] == "buy-hold-spy"
    assert detail["name"]
    assert detail["methodology_blurb"]
    assert "chosen_params" in detail
    assert "equity_series" in detail
    assert isinstance(detail["equity_series"], list)
    assert "drawdown_series" in detail
    assert "monthly_returns" in detail
    assert "tear_sheet" in detail
    assert "walkforward_windows" in detail
    assert "param_sweep" in detail
    assert "current_positions" in detail
    assert "recent_trades" in detail


def test_build_strategy_detail_unknown_returns_none(db):
    from app.services.quant_service import build_strategy_detail
    assert build_strategy_detail("does-not-exist") is None
