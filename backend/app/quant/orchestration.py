"""End-to-end inception walk-forward orchestrator.

Given a Strategy + cached bars, this function:
  1. Creates a `strategy_runs` row (status=running).
  2. Loads bars covering [inception_date, live_start_date).
  3. Builds walk-forward windows.
  4. For each window: grid-search parameters on train, evaluate best on test.
  5. Stitches OOS equity into a continuous curve.
  6. Wipes prior backtest-phase equity + trades for the strategy and writes
     the new stitched curve (`phase="backtest"`).
  7. Upserts the strategy row + chosen_params.
  8. Updates the `strategy_runs` row (status=success/failed, metrics, sweep).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import delete, insert, select, update

from app.database import (
    get_engine, strategies, strategy_equity, strategy_runs, strategy_trades,
)
from app.quant import econ_signal, news_signal
from app.quant.bars import load_close_matrix
from app.quant.cost_model import CostModel
from app.quant.engine import run_grid, run_single
from app.quant.fundamentals import get_fundamentals_batch
from app.quant.strategies.base import Strategy, StrategyContext
from app.quant.universe import get_universe
from app.quant.walkforward import build_walkforward_windows, stitch_oos_equity

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_context(
    strategy: Strategy,
    bars: pd.DataFrame,
    *,
    universe_symbols: list[str],
) -> StrategyContext:
    """Populate auxiliary signal data per strategy needs.

    Most strategies (the 6 classics + benchmark) ignore context entirely
    — they get an empty StrategyContext().
    """
    ctx = StrategyContext()
    slug = strategy.spec.slug

    if slug == "news-sentiment-momentum":
        if len(bars) > 0:
            start = bars.index[0].strftime("%Y-%m-%d")
            end = bars.index[-1].strftime("%Y-%m-%d")
            coverage = news_signal.news_coverage_matrix(
                symbols=universe_symbols, start=start, end=end,
            )
            # Phase 3 News doesn't score sentiment yet — pass zeros.
            sentiment = pd.DataFrame(
                0.0, index=coverage.index, columns=coverage.columns,
            )
            setattr(ctx, "_news_signal", {
                "coverage": coverage, "sentiment": sentiment,
            })

    elif slug == "macro-regime-overlay":
        if len(bars) > 0:
            dates = bars.index.strftime("%Y-%m-%d")
            labels = [econ_signal.classify_regime(as_of=d) for d in dates]
            regime = pd.Series(labels, index=dates)
            setattr(ctx, "_regime", regime)

    elif slug == "multi-factor-combo":
        ctx.fundamentals = get_fundamentals_batch(universe_symbols)

    return ctx


def _upsert_strategy_row(strategy: Strategy, chosen_params: dict) -> None:
    cost_model = CostModel(allow_short=strategy.spec.allow_short)
    with get_engine().begin() as conn:
        conn.execute(
            delete(strategies).where(strategies.c.slug == strategy.spec.slug)
        )
        conn.execute(insert(strategies).values(
            slug=strategy.spec.slug,
            name=strategy.spec.name,
            category=strategy.spec.category,
            methodology_blurb=strategy.spec.methodology_blurb,
            universe_kind=strategy.spec.universe_kind,
            inception_date=strategy.spec.inception_date,
            live_start_date=strategy.spec.live_start_date,
            chosen_params=json.dumps(chosen_params),
            cost_model=json.dumps(cost_model.to_dict()),
            enabled=1,
            last_forward_step_date=None,
        ))


def _wipe_backtest_rows(slug: str) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            delete(strategy_equity).where(
                (strategy_equity.c.strategy_slug == slug)
                & (strategy_equity.c.phase == "backtest")
            )
        )
        conn.execute(
            delete(strategy_trades).where(
                (strategy_trades.c.strategy_slug == slug)
                & (strategy_trades.c.phase == "backtest")
            )
        )


def _write_equity_curve(slug: str, equity: pd.Series) -> None:
    if equity.empty:
        return
    rows = []
    prev = None
    for ts, val in equity.items():
        ret = 0.0 if prev is None or prev == 0 else float(val / prev - 1.0)
        rows.append({
            "strategy_slug": slug,
            "date": ts.strftime("%Y-%m-%d"),
            "equity": float(val),
            "cash": 0.0,
            "gross_exposure": float(val),
            "net_exposure": float(val),
            "daily_return": ret,
            "phase": "backtest",
        })
        prev = val
    with get_engine().begin() as conn:
        conn.execute(insert(strategy_equity), rows)


def _write_trades(slug: str, trades: pd.DataFrame) -> None:
    if trades is None or trades.empty:
        return
    rows = []
    for _, t in trades.iterrows():
        rows.append({
            "strategy_slug": slug,
            "date": str(t["date"]),
            "symbol": str(t["symbol"]),
            "side": str(t["side"]),
            "qty": int(t["qty"]),
            "price": float(t["price"]),
            "commission": float(t.get("commission", 0.0)),
            "notional": float(t["notional"]),
            "phase": "backtest",
        })
    with get_engine().begin() as conn:
        conn.execute(insert(strategy_trades), rows)


def inception_walkforward(
    strategy: Strategy,
    *,
    train_years: int = 3,
    test_years: int = 1,
    step_months: int = 6,
    initial_equity: float = 100_000.0,
) -> int:
    """Run the full inception walk-forward for `strategy`.

    Returns the strategy_runs.id of the created run.
    """
    # 1. Create the run row.
    with get_engine().begin() as conn:
        run_id = conn.execute(insert(strategy_runs).values(
            strategy_slug=strategy.spec.slug,
            run_kind="inception-walkforward",
            started_at=_now_iso(),
            finished_at=None,
            status="running",
            progress=json.dumps({"windows_done": 0, "windows_total": 0}),
            error=None,
            summary_metrics=None,
            walkforward_windows=None,
            param_sweep=None,
        )).inserted_primary_key[0]

    try:
        # 2. Load bars.
        symbols = list(get_universe(strategy.spec.universe_kind))
        bars = load_close_matrix(
            symbols,
            start=strategy.spec.inception_date,
            end=strategy.spec.live_start_date,
        )
        if bars.empty:
            raise RuntimeError(
                f"no bars in cache for {strategy.spec.slug}; run fetch_and_cache first"
            )

        # 2b. Build strategy context (signal data for alpha strategies).
        ctx = _build_context(strategy, bars, universe_symbols=symbols)

        # 3. Build windows.
        windows = build_walkforward_windows(
            bars.index, train_years=train_years,
            test_years=test_years, step_months=step_months,
        )
        if not windows:
            raise RuntimeError("insufficient data for any walk-forward window")

        cost_model = CostModel(allow_short=strategy.spec.allow_short)

        sweep_acc: list[dict] = []
        oos_equity_segments: list[pd.Series] = []
        oos_trades: list[pd.DataFrame] = []
        window_records: list[dict] = []

        # 4. Per-window grid search + OOS evaluation.
        for i, w in enumerate(windows):
            train_bars = bars.loc[w.train_start:w.train_end]
            test_bars = bars.loc[w.test_start:w.test_end]

            constraint = None
            if "fast" in strategy.sweep_grid and "slow" in strategy.sweep_grid:
                constraint = lambda p: p["fast"] < p["slow"]   # noqa: E731

            grid_df = run_grid(
                strategy, train_bars, grid=strategy.sweep_grid,
                cost_model=cost_model, initial_equity=initial_equity,
                constraint=constraint,
                ctx=ctx,
            )

            if strategy.sweep_grid and not grid_df.empty:
                # Drop degenerate combos: zero total_return implies no trades
                # were taken, which makes Sharpe meaningless (often nan/inf).
                viable = grid_df[
                    grid_df["sharpe"].replace([float("inf"), float("-inf")], pd.NA).notna()
                    & (grid_df["total_return"].abs() > 1e-9)
                ]
                if viable.empty:
                    viable = grid_df  # fall back if everything is degenerate
                best_row = viable.sort_values("sharpe", ascending=False).iloc[0]
                best_params = {
                    k: best_row[k] for k in strategy.sweep_grid.keys()
                }
                # Cast numpy ints back to python ints for JSON.
                best_params = {
                    k: int(v) if hasattr(v, "item") and float(v).is_integer()
                    else (float(v) if hasattr(v, "item") else v)
                    for k, v in best_params.items()
                }
                for _, row in grid_df.iterrows():
                    cell = {
                        "params": {
                            k: int(row[k]) if hasattr(row[k], "item")
                                              and float(row[k]).is_integer()
                            else (float(row[k]) if hasattr(row[k], "item") else row[k])
                            for k in strategy.sweep_grid.keys()
                        },
                        "sharpe": float(row["sharpe"]),
                    }
                    sweep_acc.append(cell)
            else:
                best_params = {}

            oos = run_single(
                strategy, test_bars, params=best_params,
                cost_model=cost_model, initial_equity=initial_equity,
                ctx=ctx,
            )
            oos_equity_segments.append(oos.equity)
            oos_trades.append(oos.trades.assign(strategy_slug=strategy.spec.slug))
            window_records.append({
                "train_start": w.train_start, "train_end": w.train_end,
                "test_start": w.test_start, "test_end": w.test_end,
                "chosen_params": best_params,
                "oos_metrics": oos.metrics,
            })

            # Heartbeat
            with get_engine().begin() as conn:
                conn.execute(update(strategy_runs).where(
                    strategy_runs.c.id == run_id
                ).values(progress=json.dumps({
                    "windows_done": i + 1, "windows_total": len(windows),
                })))

        # 5. Stitch OOS equity.
        stitched = stitch_oos_equity(oos_equity_segments)
        all_trades = pd.concat(oos_trades, ignore_index=True) if oos_trades else pd.DataFrame()

        # Summary metrics from the stitched curve.
        if len(stitched) >= 2:
            rets = stitched.pct_change().dropna()
            total_return = float(stitched.iloc[-1] / stitched.iloc[0] - 1.0)
            sharpe = float(rets.mean() / rets.std() * (252 ** 0.5)) if rets.std() > 0 else 0.0
            roll_max = stitched.cummax()
            dd = (stitched - roll_max) / roll_max
            max_dd = float(dd.min())
        else:
            total_return, sharpe, max_dd = 0.0, 0.0, 0.0

        summary = {
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "windows": len(windows),
            "stitched_points": int(len(stitched)),
        }

        # 6 & 7. Wipe + write equity/trades and upsert the strategy row.
        chosen_params = window_records[-1]["chosen_params"] if window_records else {}
        _wipe_backtest_rows(strategy.spec.slug)
        _write_equity_curve(strategy.spec.slug, stitched)
        _write_trades(strategy.spec.slug, all_trades)
        _upsert_strategy_row(strategy, chosen_params)

        # 8. Mark run success.
        with get_engine().begin() as conn:
            conn.execute(update(strategy_runs).where(
                strategy_runs.c.id == run_id
            ).values(
                finished_at=_now_iso(),
                status="success",
                summary_metrics=json.dumps(summary),
                walkforward_windows=json.dumps(window_records),
                param_sweep=json.dumps(sweep_acc),
            ))

        return run_id

    except Exception as e:
        logger.exception("inception_walkforward failed for %s", strategy.spec.slug)
        with get_engine().begin() as conn:
            conn.execute(update(strategy_runs).where(
                strategy_runs.c.id == run_id
            ).values(
                finished_at=_now_iso(),
                status="failed",
                error=str(e),
            ))
        raise
