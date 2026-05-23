import json
from datetime import date as _date

import pandas as pd
from sqlalchemy import insert, select

from app.database import (
    bar_cache, get_engine, strategies, strategy_equity,
    strategy_positions, strategy_trades,
)
from app.quant.bars import upsert_bars
from app.quant.runner import forward_step, forward_step_all


def _seed_strategy_row(slug: str, *, live_start: str, last_step: str | None = None,
                       cost_model_json: str = '{"commission":0,"slippage_bps":5,"allow_short":false}'):
    with get_engine().begin() as conn:
        conn.execute(insert(strategies).values(
            slug=slug, name=slug, category="benchmark",
            methodology_blurb="x", universe_kind="spy",
            inception_date="2024-01-02", live_start_date=live_start,
            chosen_params="{}", cost_model=cost_model_json,
            enabled=1, last_forward_step_date=last_step,
        ))


def _seed_spy_bars(start: str, n: int = 30, base_price: float = 100.0):
    idx = pd.bdate_range(start, periods=n)
    prices = [base_price * (1 + 0.001 * i) for i in range(n)]
    df = pd.DataFrame({
        "Open": prices, "High": [p * 1.001 for p in prices],
        "Low": [p * 0.999 for p in prices],
        "Close": prices, "Adj Close": prices,
        "Volume": [1_000_000] * n,
    }, index=idx)
    upsert_bars("SPY", df)


def test_forward_step_appends_one_equity_row(db):
    _seed_spy_bars("2025-01-02", n=30)
    _seed_strategy_row("buy-hold-spy", live_start="2025-01-02")
    forward_step("buy-hold-spy", target_date="2025-01-15")
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(strategy_equity).where(
                (strategy_equity.c.strategy_slug == "buy-hold-spy")
                & (strategy_equity.c.phase == "forward")
            )
        ).all()
    assert len(rows) == 1
    assert rows[0].date == "2025-01-15"


def test_forward_step_idempotent(db):
    _seed_spy_bars("2025-01-02", n=30)
    _seed_strategy_row("buy-hold-spy", live_start="2025-01-02")
    forward_step("buy-hold-spy", target_date="2025-01-15")
    # Re-running same day must NOT duplicate.
    forward_step("buy-hold-spy", target_date="2025-01-15")
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(strategy_equity).where(
                strategy_equity.c.strategy_slug == "buy-hold-spy"
            )
        ).all()
    assert len(rows) == 1


def test_forward_step_refuses_to_go_backwards(db):
    _seed_spy_bars("2025-01-02", n=30)
    _seed_strategy_row("buy-hold-spy", live_start="2025-01-02",
                       last_step="2025-01-15")
    forward_step("buy-hold-spy", target_date="2025-01-14")  # earlier — no-op
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(strategy_equity).where(
                strategy_equity.c.strategy_slug == "buy-hold-spy"
            )
        ).all()
    assert len(rows) == 0


def test_forward_step_advances_last_forward_step_date(db):
    _seed_spy_bars("2025-01-02", n=30)
    _seed_strategy_row("buy-hold-spy", live_start="2025-01-02")
    forward_step("buy-hold-spy", target_date="2025-01-15")
    with get_engine().begin() as conn:
        row = conn.execute(
            select(strategies.c.last_forward_step_date).where(
                strategies.c.slug == "buy-hold-spy"
            )
        ).first()
    assert row[0] == "2025-01-15"


def test_forward_step_all_catches_up_multiple_days(db):
    _seed_spy_bars("2025-01-02", n=30)
    _seed_strategy_row("buy-hold-spy", live_start="2025-01-13",
                       last_step="2025-01-13")
    # Target three business days ahead. Catch-up should write 3 rows.
    forward_step_all(target_date="2025-01-16")
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(strategy_equity).where(
                (strategy_equity.c.strategy_slug == "buy-hold-spy")
                & (strategy_equity.c.phase == "forward")
            ).order_by(strategy_equity.c.date)
        ).all()
    assert len(rows) == 3
    assert [r.date for r in rows] == ["2025-01-14", "2025-01-15", "2025-01-16"]


def test_forward_step_all_caps_at_30_days(db):
    _seed_spy_bars("2025-01-02", n=60)
    _seed_strategy_row("buy-hold-spy", live_start="2025-01-02",
                       last_step="2025-01-02")
    # Far-future target — should advance at most 30 business days.
    forward_step_all(target_date="2025-12-31")
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(strategy_equity).where(
                strategy_equity.c.strategy_slug == "buy-hold-spy"
            )
        ).all()
    assert len(rows) <= 30


def test_forward_step_all_skips_disabled(db):
    _seed_spy_bars("2025-01-02", n=30)
    _seed_strategy_row("buy-hold-spy", live_start="2025-01-02")
    with get_engine().begin() as conn:
        from sqlalchemy import update as _upd
        conn.execute(_upd(strategies).where(
            strategies.c.slug == "buy-hold-spy"
        ).values(enabled=0))
    forward_step_all(target_date="2025-01-15")
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(strategy_equity).where(
                strategy_equity.c.strategy_slug == "buy-hold-spy"
            )
        ).all()
    assert len(rows) == 0
