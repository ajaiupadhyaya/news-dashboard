import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import insert, select

from app.auth import require_auth
from app.cache import cache
from app.database import (
    get_engine, strategies as strategies_t, strategy_runs, strategy_trades,
)
from app.quant.jobs import run_inception_walkforward_async
from app.services import quant_service

router = APIRouter(prefix="/api/quant", dependencies=[Depends(require_auth)])


@router.get("/overview")
def overview():
    return cache.get_or_compute("quant:overview", quant_service.build_overview)


@router.get("/strategy/{slug}")
def strategy_detail(slug: str):
    key = f"quant:strategy:{slug}"
    result = cache.get_or_compute(
        key, lambda: quant_service.build_strategy_detail(slug)
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"No strategy '{slug}'")
    return result


@router.get("/strategy/{slug}/trades")
def strategy_trades_endpoint(
    slug: str,
    cursor: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    with get_engine().begin() as conn:
        query = select(strategy_trades).where(
            strategy_trades.c.strategy_slug == slug
        ).order_by(
            strategy_trades.c.date.desc(), strategy_trades.c.id.desc()
        )
        if cursor:
            # cursor format: "<date>:<id>"
            try:
                cur_date, cur_id = cursor.split(":")
                cur_id = int(cur_id)
                query = query.where(
                    (strategy_trades.c.date < cur_date)
                    | ((strategy_trades.c.date == cur_date)
                       & (strategy_trades.c.id < cur_id))
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="Bad cursor")
        query = query.limit(limit + 1)
        rows = conn.execute(query).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = f"{rows[-1].date}:{rows[-1].id}" if has_more and rows else None
    return {
        "trades": [{
            "id": r.id, "date": r.date, "symbol": r.symbol,
            "side": r.side, "qty": r.qty, "price": float(r.price),
            "commission": float(r.commission), "notional": float(r.notional),
            "phase": r.phase,
        } for r in rows],
        "next_cursor": next_cursor,
    }


@router.post("/strategy/{slug}/recompute-backtest", status_code=202)
def recompute_backtest(slug: str, background_tasks: BackgroundTasks):
    with get_engine().begin() as conn:
        s = conn.execute(
            select(strategies_t).where(strategies_t.c.slug == slug)
        ).first()
        if s is None:
            raise HTTPException(status_code=404, detail=f"No strategy '{slug}'")
        in_flight = conn.execute(
            select(strategy_runs).where(
                (strategy_runs.c.strategy_slug == slug)
                & (strategy_runs.c.status.in_(("pending", "running")))
            ).limit(1)
        ).first()
        if in_flight is not None:
            raise HTTPException(
                status_code=409,
                detail="A recompute is already in flight for this strategy",
            )
        rid = conn.execute(insert(strategy_runs).values(
            strategy_slug=slug,
            run_kind="inception-walkforward",
            started_at="",
            finished_at=None,
            status="pending",
            progress="{}",
            error=None,
            summary_metrics=None,
            walkforward_windows=None,
            param_sweep=None,
        )).inserted_primary_key[0]

    background_tasks.add_task(run_inception_walkforward_async, slug)
    return {"run_id": rid, "status": "pending"}


@router.get("/runs/{run_id}")
def get_run(run_id: int):
    with get_engine().begin() as conn:
        row = conn.execute(
            select(strategy_runs).where(strategy_runs.c.id == run_id)
        ).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No run {run_id}")
    return {
        "id": row.id, "strategy_slug": row.strategy_slug,
        "run_kind": row.run_kind, "status": row.status,
        "started_at": row.started_at, "finished_at": row.finished_at,
        "progress": json.loads(row.progress or "{}"),
        "error": row.error,
        "summary_metrics": json.loads(row.summary_metrics) if row.summary_metrics else None,
    }
