"""Top-level job functions for APScheduler + FastAPI BackgroundTasks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select

from app.database import get_engine, strategies as strategies_t
from app.quant.bars import fetch_and_cache
from app.quant.orchestration import inception_walkforward
from app.quant.registry import get_strategy
from app.quant.runner import forward_step_all
from app.quant.universe import get_universe

logger = logging.getLogger(__name__)


def _today_iso_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def warm_quant_bars(*, target_date: str | None = None,
                    history_days: int = 90) -> int:
    """Refresh bar_cache covering [target - history, target] for every
    universe used by enabled strategies. Default `target_date` = today UTC.
    """
    target = target_date or _today_iso_utc()
    start = (pd.Timestamp(target) - pd.Timedelta(days=history_days)).strftime("%Y-%m-%d")

    with get_engine().begin() as conn:
        rows = conn.execute(
            select(strategies_t.c.universe_kind).where(strategies_t.c.enabled == 1)
        ).all()
    if not rows:
        return 0

    universe_kinds = {r[0] for r in rows}
    symbols: set[str] = set()
    for kind in universe_kinds:
        try:
            symbols.update(get_universe(kind))
        except ValueError:
            logger.warning("warm_quant_bars: unknown universe_kind=%s", kind)
    if not symbols:
        return 0
    return fetch_and_cache(symbols=sorted(symbols), start=start, end=target)


def forward_step_all_strategies(*, target_date: str | None = None) -> dict:
    target = target_date or _today_iso_utc()
    try:
        return forward_step_all(target_date=target)
    except Exception:
        logger.exception("forward_step_all_strategies failed")
        return {}


def run_inception_walkforward_async(slug: str) -> int:
    """Synchronous wrapper around `orchestration.inception_walkforward`.

    Returns the strategy_runs.id of the created run.
    """
    strategy = get_strategy(slug)
    return inception_walkforward(strategy)
