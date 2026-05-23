"""Quant Lab service layer — assembles API payloads from the DB."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import select

from app.database import (
    bar_cache, get_engine, strategies as strategies_t,
    strategy_equity, strategy_positions, strategy_runs, strategy_trades,
)


def _load_equity(slug: str) -> pd.DataFrame:
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(strategy_equity).where(
                strategy_equity.c.strategy_slug == slug
            ).order_by(strategy_equity.c.date)
        ).all()
    if not rows:
        return pd.DataFrame(columns=["date", "equity", "phase", "daily_return"])
    return pd.DataFrame([{
        "date": r.date, "equity": float(r.equity), "phase": r.phase,
        "daily_return": float(r.daily_return),
    } for r in rows])


def _metrics_from_equity(eq: pd.Series) -> dict:
    if len(eq) < 2 or eq.iloc[0] == 0:
        return {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}
    rets = eq.pct_change().dropna()
    total_return = float(eq.iloc[-1] / eq.iloc[0] - 1.0)
    sharpe = float(rets.mean() / rets.std() * (252 ** 0.5)) if rets.std() else 0.0
    roll_max = eq.cummax()
    dd = (eq - roll_max) / roll_max
    max_dd = float(dd.min())
    return {
        "total_return": total_return, "sharpe": sharpe, "max_drawdown": max_dd,
    }


def build_overview() -> dict[str, Any]:
    with get_engine().begin() as conn:
        strat_rows = conn.execute(
            select(strategies_t).where(strategies_t.c.enabled == 1)
            .order_by(strategies_t.c.category, strategies_t.c.slug)
        ).all()
        recent_trades = conn.execute(
            select(strategy_trades).order_by(
                strategy_trades.c.date.desc(), strategy_trades.c.id.desc()
            ).limit(20)
        ).all()
        latest_bar = conn.execute(
            select(bar_cache.c.fetched_at).order_by(
                bar_cache.c.fetched_at.desc()
            ).limit(1)
        ).first()

    leaderboard = []
    normalized_per_slug: list[pd.Series] = []
    for s in strat_rows:
        eq_df = _load_equity(s.slug)
        forward = eq_df[eq_df["phase"] == "forward"]
        if forward.empty:
            forward = eq_df   # fall back to full history (backtest+forward)
        sparkline = forward["equity"].astype(float).tolist()[-30:]
        live_since = forward["date"].iloc[0] if not forward.empty else None
        m = _metrics_from_equity(forward["equity"])
        leaderboard.append({
            "slug": s.slug, "name": s.name, "category": s.category,
            "sparkline": sparkline,
            "live_since": live_since,
            "total_return": m["total_return"],
            "sharpe": m["sharpe"],
            "max_drawdown": m["max_drawdown"],
        })
        # Combined equity: rescale each strategy to start at 100k.
        if not forward.empty:
            scaled = forward.set_index("date")["equity"]
            scaled = scaled * (100_000.0 / scaled.iloc[0])
            normalized_per_slug.append(scaled)

    # Hero combined: mean across the normalized series at each date.
    if normalized_per_slug:
        wide = pd.concat(normalized_per_slug, axis=1).sort_index()
        hero_series = wide.mean(axis=1).dropna()
        hero_equity = [
            {"date": d, "equity": float(v)} for d, v in hero_series.items()
        ]
    else:
        hero_equity = []

    trades = [{
        "strategy_slug": r.strategy_slug, "date": r.date,
        "symbol": r.symbol, "side": r.side, "qty": r.qty,
        "price": float(r.price), "notional": float(r.notional),
        "phase": r.phase,
    } for r in recent_trades]

    return {
        "leaderboard": leaderboard,
        "hero_equity": hero_equity,
        "recent_trades": trades,
        "universe_health": {
            "latest_bar_fetched_at": latest_bar[0] if latest_bar else None,
            "last_forward_step_per_strategy": {
                s.slug: s.last_forward_step_date for s in strat_rows
            },
        },
    }


def build_strategy_detail(slug: str) -> dict | None:
    with get_engine().begin() as conn:
        s = conn.execute(
            select(strategies_t).where(strategies_t.c.slug == slug)
        ).first()
        if s is None:
            return None
        run = conn.execute(
            select(strategy_runs).where(
                (strategy_runs.c.strategy_slug == slug)
                & (strategy_runs.c.status == "success")
            ).order_by(strategy_runs.c.id.desc()).limit(1)
        ).first()
        position_rows = conn.execute(
            select(strategy_positions).where(
                strategy_positions.c.strategy_slug == slug
            )
        ).all()
        trade_rows = conn.execute(
            select(strategy_trades).where(
                strategy_trades.c.strategy_slug == slug
            ).order_by(
                strategy_trades.c.date.desc(), strategy_trades.c.id.desc()
            ).limit(100)
        ).all()

    eq_df = _load_equity(slug)
    equity_series = [
        {"date": r["date"], "equity": float(r["equity"]),
         "phase": r["phase"], "daily_return": float(r["daily_return"])}
        for _, r in eq_df.iterrows()
    ]
    if not eq_df.empty:
        eq = eq_df["equity"].astype(float)
        roll_max = eq.cummax()
        dd = (eq - roll_max) / roll_max
        drawdown_series = [
            {"date": d, "drawdown": float(v)}
            for d, v in zip(eq_df["date"].tolist(), dd.tolist())
        ]
        # Monthly returns matrix
        ts = eq_df.copy()
        ts["date"] = pd.to_datetime(ts["date"])
        ts = ts.set_index("date")["equity"]
        monthly = ts.resample("ME").last().pct_change().dropna()
        matrix: dict[str, dict[int, float]] = {}
        for idx, val in monthly.items():
            yr = str(idx.year)
            matrix.setdefault(yr, {})[int(idx.month)] = float(val)
        tear_sheet = _metrics_from_equity(eq)
    else:
        drawdown_series = []
        matrix = {}
        tear_sheet = {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}

    return {
        "slug": s.slug, "name": s.name, "category": s.category,
        "methodology_blurb": s.methodology_blurb,
        "universe_kind": s.universe_kind,
        "inception_date": s.inception_date,
        "live_start_date": s.live_start_date,
        "chosen_params": json.loads(s.chosen_params or "{}"),
        "cost_model": json.loads(s.cost_model or "{}"),
        "last_forward_step_date": s.last_forward_step_date,
        "equity_series": equity_series,
        "drawdown_series": drawdown_series,
        "monthly_returns": matrix,
        "tear_sheet": tear_sheet,
        "walkforward_windows": (
            json.loads(run.walkforward_windows) if run and run.walkforward_windows else []
        ),
        "param_sweep": (
            json.loads(run.param_sweep) if run and run.param_sweep else []
        ),
        "current_positions": [{
            "symbol": p.symbol, "qty": p.qty, "avg_cost": float(p.avg_cost),
            "opened_at": p.opened_at,
        } for p in position_rows],
        "recent_trades": [{
            "id": t.id, "date": t.date, "symbol": t.symbol,
            "side": t.side, "qty": t.qty, "price": float(t.price),
            "commission": float(t.commission), "notional": float(t.notional),
            "phase": t.phase,
        } for t in trade_rows],
    }
