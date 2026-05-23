"""Forward-step runner — extends each strategy's equity curve by one day.

Pure SQL-driven loop; idempotent on (strategy_slug, date). The same cost
model and signal logic the backtest used are reused here via the engine
primitives, so backtest and forward results stay numerically consistent.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import insert, select, update

from app.database import (
    get_engine, strategies as strategies_t, strategy_equity, strategy_positions,
    strategy_trades,
)
from app.quant.bars import load_close_matrix
from app.quant.cost_model import CostModel, target_qty_from_weight
from app.quant.engine import simulate_fills
from app.quant.registry import STRATEGIES, get_strategy
from app.quant.strategies.base import StrategyContext
from app.quant.universe import get_universe

logger = logging.getLogger(__name__)

_MAX_CATCHUP_DAYS = 30


def _load_strategy_row(slug: str) -> dict | None:
    with get_engine().begin() as conn:
        row = conn.execute(
            select(strategies_t).where(strategies_t.c.slug == slug)
        ).first()
    if row is None:
        return None
    return dict(row._mapping)


def _current_positions(slug: str) -> dict[str, dict]:
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(strategy_positions).where(
                strategy_positions.c.strategy_slug == slug
            )
        ).all()
    return {r.symbol: {"qty": r.qty, "avg_cost": r.avg_cost} for r in rows}


def _current_equity(slug: str, *, fallback: float = 100_000.0) -> float:
    with get_engine().begin() as conn:
        row = conn.execute(
            select(strategy_equity.c.equity).where(
                strategy_equity.c.strategy_slug == slug
            ).order_by(strategy_equity.c.date.desc()).limit(1)
        ).first()
    return float(row[0]) if row else fallback


def forward_step(slug: str, *, target_date: str) -> bool:
    """Advance `slug` by exactly one day to `target_date`.

    Returns True if a step was written, False if a no-op (idempotent or
    target_date <= last_forward_step_date).
    """
    row = _load_strategy_row(slug)
    if row is None:
        logger.warning("forward_step: unknown strategy %s", slug)
        return False
    if not row["enabled"]:
        return False
    last = row["last_forward_step_date"]
    if last is not None and target_date <= last:
        return False

    try:
        strategy = get_strategy(slug)
    except KeyError:
        # Strategy row exists in DB but not in code registry.
        logger.warning("forward_step: %s not in code registry; skipping", slug)
        return False

    cost_model = CostModel.from_dict(json.loads(row["cost_model"]))
    chosen_params = json.loads(row["chosen_params"]) if row["chosen_params"] else {}

    universe_symbols = list(get_universe(strategy.spec.universe_kind))

    # Need enough history for the strategy's lookbacks — load 400 bars back.
    end = target_date
    start_dt = pd.Timestamp(end) - pd.Timedelta(days=600)
    start = start_dt.strftime("%Y-%m-%d")
    bars = load_close_matrix(universe_symbols, start=start, end=end)
    if bars.empty or pd.Timestamp(target_date) not in bars.index:
        logger.warning("forward_step %s: no bars for %s", slug, target_date)
        return False

    # Build context (no-op for non-alpha strategies).
    from app.quant.orchestration import _build_context
    ctx = _build_context(strategy, bars, universe_symbols=universe_symbols)

    weights = strategy.generate_signals(bars, chosen_params, ctx)
    target_row = weights.loc[pd.Timestamp(target_date)].fillna(0.0)
    prices_row = bars.loc[pd.Timestamp(target_date)].dropna()

    current_equity_val = _current_equity(slug, fallback=100_000.0)
    current_positions = _current_positions(slug)
    target_positions = {}
    for sym, weight in target_row.items():
        if weight == 0:
            continue
        px = float(prices_row.get(sym, 0.0))
        if px <= 0:
            continue
        qty = target_qty_from_weight(weight=float(weight),
                                     equity=current_equity_val, price=px)
        if qty != 0:
            target_positions[sym] = {"qty": qty, "weight": float(weight)}

    fills, new_positions = simulate_fills(
        current_positions=current_positions,
        target_positions=target_positions,
        prices={s: float(prices_row[s]) for s in prices_row.index},
        cost_model=cost_model,
    )

    # Mark-to-market new equity.
    cash = current_equity_val
    for f in fills:
        signed_qty = f["qty"] if f["side"] in ("buy", "cover") else -f["qty"]
        cash -= signed_qty * f["price"]
        cash -= f["commission"]
    new_market_value = 0.0
    for sym, pos in new_positions.items():
        px = float(prices_row.get(sym, pos["avg_cost"]))
        new_market_value += pos["qty"] * px
    new_equity = cash + new_market_value
    daily_return = (new_equity / current_equity_val - 1.0) if current_equity_val else 0.0
    gross = sum(abs(pos["qty"]) * float(prices_row.get(sym, pos["avg_cost"]))
                for sym, pos in new_positions.items())
    net = sum(pos["qty"] * float(prices_row.get(sym, pos["avg_cost"]))
              for sym, pos in new_positions.items())

    with get_engine().begin() as conn:
        # 1. Write trades.
        if fills:
            conn.execute(insert(strategy_trades), [
                {"strategy_slug": slug, "date": target_date, "symbol": f["symbol"],
                 "side": f["side"], "qty": f["qty"], "price": f["price"],
                 "commission": f["commission"], "notional": f["notional"],
                 "phase": "forward"}
                for f in fills
            ])
        # 2. Upsert positions.
        from sqlalchemy import delete as _del
        conn.execute(_del(strategy_positions).where(
            strategy_positions.c.strategy_slug == slug
        ))
        if new_positions:
            conn.execute(insert(strategy_positions), [
                {"strategy_slug": slug, "symbol": sym,
                 "qty": pos["qty"], "avg_cost": pos["avg_cost"],
                 "opened_at": target_date, "last_marked_at": target_date}
                for sym, pos in new_positions.items()
            ])
        # 3. Insert equity row (idempotent — PK is slug+date).
        conn.execute(insert(strategy_equity).values(
            strategy_slug=slug, date=target_date,
            equity=new_equity, cash=cash,
            gross_exposure=gross, net_exposure=net,
            daily_return=daily_return, phase="forward",
        ))
        # 4. Advance the strategy row.
        conn.execute(update(strategies_t).where(
            strategies_t.c.slug == slug
        ).values(last_forward_step_date=target_date))

    logger.info("forward_step %s -> %s (equity=%.2f, fills=%d)",
                slug, target_date, new_equity, len(fills))
    return True


def forward_step_all(target_date: str) -> dict:
    """Catch every enabled strategy up to `target_date`.

    Bounded to `_MAX_CATCHUP_DAYS` business days per strategy per call.
    Returns a per-slug summary dict.
    """
    summary: dict[str, dict] = {}
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(strategies_t.c.slug, strategies_t.c.last_forward_step_date,
                   strategies_t.c.enabled)
        ).all()
    for slug, last_step, enabled in rows:
        if not enabled:
            summary[slug] = {"skipped": "disabled"}
            continue
        start = last_step or "1900-01-01"
        days = pd.bdate_range(
            (pd.Timestamp(start) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            target_date,
        )
        if len(days) == 0:
            summary[slug] = {"steps": 0}
            continue
        days = days[:_MAX_CATCHUP_DAYS]
        n_done = 0
        for d in days:
            try:
                if forward_step(slug, target_date=d.strftime("%Y-%m-%d")):
                    n_done += 1
            except Exception:
                logger.exception("forward_step %s -> %s failed", slug, d)
                break
        summary[slug] = {"steps": n_done}
    return summary
