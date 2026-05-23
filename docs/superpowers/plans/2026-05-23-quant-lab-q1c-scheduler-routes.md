# Quant Lab Q1c — Forward-Step Runner + Scheduler + API Routes

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Connect the Quant Lab to the live FastAPI app. Add the continuous daily forward-step runner that extends each strategy's equity curve by one day; the APScheduler jobs that warm the bar cache and trigger the forward step after each US market close; the `app.services.quant_service` orchestration layer; the `/api/quant/*` HTTP routes; and the background-job machinery for `POST /strategy/{slug}/recompute-backtest`. After Q1c the backend serves a complete Quant Lab API; Q1d wires up the frontend.

**Architecture:** Builds on Q1a + Q1b. The forward-step runner uses the existing `engine.simulate_fills` primitive and the same cost model as the backtest path — so backtest and forward stay numerically consistent. Scheduler jobs follow the existing `warm_*` pattern in `app/scheduler.py`. Routes follow the existing `app/routes/*.py` pattern (APIRouter with `require_auth` dependency, prefixed `/api/quant`). Background jobs run via FastAPI's `BackgroundTasks` — sufficient for one-at-a-time strategy recomputes.

**Tech Stack:** FastAPI, SQLAlchemy Core, APScheduler (existing), pytest. No new third-party deps.

**Spec:** `docs/superpowers/specs/2026-05-22-quant-lab-design.md` §4.2 (forward-step), §7 (API surface), §11 (perf budget).

**Out of scope (deferred to Q1d):**
- Frontend `/quant` route + components
- Vercel deploy
- Playwright E2E

---

## Background — State at the time of this plan

`main` is at the Q1b merge commit (`3e03651`). 270 backend tests passing. In place:
- 9 strategies in the registry (`app.quant.registry.STRATEGIES`).
- `app.quant.engine.run_single`, `run_grid`, `simulate_fills`, `EngineResult`.
- `app.quant.orchestration.inception_walkforward(strategy, ...)` end-to-end.
- 6 quant tables: `bar_cache`, `strategies`, `strategy_runs`, `strategy_equity`, `strategy_trades`, `strategy_positions`.

---

## File Map

**New:**
- `backend/app/quant/runner.py` — forward-step loop
- `backend/app/quant/jobs.py` — top-level functions called by APScheduler (`warm_quant_bars`, `forward_step_all_strategies`, `run_inception_walkforward_async`)
- `backend/app/services/quant_service.py` — service layer that assembles API responses
- `backend/app/routes/quant.py` — HTTP routes
- `backend/tests/test_quant_runner.py`
- `backend/tests/test_quant_jobs.py`
- `backend/tests/test_quant_service.py`
- `backend/tests/test_quant_routes.py`

**Modified:**
- `backend/app/main.py` — `include_router(quant_router)`
- `backend/app/scheduler.py` — wire `warm_quant_bars` + `forward_step_all_strategies` jobs

---

## Task 1: Forward-step runner

**Files:**
- Create: `backend/app/quant/runner.py`
- Create: `backend/tests/test_quant_runner.py`

The runner extends each enabled strategy's equity curve by one day. Idempotent on `(strategy_slug, date)`. Refuses to advance backwards. Catch-up loop bounded to 30 days per call.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_runner.py`:

```python
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
```

Run — expect 7 FAIL.

- [ ] **Step 2: Implement**

Create `backend/app/quant/runner.py`:

```python
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
```

- [ ] **Step 3: Tests + commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard/.claude/worktrees/quant-lab-q1c/backend && /Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -m pytest tests/test_quant_runner.py -v
```
Expect 7 PASS.

Full suite: 277.

```bash
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): forward-step runner — daily idempotent equity-curve extender

forward_step(slug, target_date) advances one strategy by exactly one day;
forward_step_all(target_date) catches every enabled strategy up, capped
at 30 business days per call. Uses the existing engine.simulate_fills
primitive so backtest and forward paths stay numerically consistent.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Background-job helper for inception walk-forward

**Files:**
- Create: `backend/app/quant/jobs.py`
- Create: `backend/tests/test_quant_jobs.py`

Three top-level functions that APScheduler + FastAPI BackgroundTasks call:
- `warm_quant_bars(target_date)` — refresh `bar_cache` for the universe used by enabled strategies.
- `forward_step_all_strategies()` — thin wrapper around `runner.forward_step_all` that picks "today's" target date.
- `run_inception_walkforward_async(slug)` — wraps `orchestration.inception_walkforward` with status updates on the `strategy_runs` row (already handled by `inception_walkforward`).

- [ ] **Step 1: Test**

```python
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
```

- [ ] **Step 2: Implement**

Create `backend/app/quant/jobs.py`:

```python
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
```

- [ ] **Step 3: Tests + commit**

Expect 3 PASS. Full suite: 280.

```bash
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): jobs module — top-level functions for scheduler + BG tasks

warm_quant_bars refreshes bar_cache for the universes used by enabled
strategies. forward_step_all_strategies is the scheduler entrypoint.
run_inception_walkforward_async wraps the orchestrator for the
recompute-backtest HTTP endpoint.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: APScheduler wiring

**Files:**
- Modify: `backend/app/scheduler.py`
- Modify: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Extend the existing scheduler tests**

Read `backend/tests/test_scheduler.py`. The existing pattern verifies that `start_scheduler()` registers each warm-job ID. Add two assertions: `"warm_quant_bars"` and `"forward_step_all_strategies"` appear in the registered job list.

- [ ] **Step 2: Extend `backend/app/scheduler.py`**

Add to the top imports:

```python
from app.quant import jobs as quant_jobs
```

Add two new wrapper functions in the same try/except style as the existing `warm_*` functions:

```python
def warm_quant_bars() -> None:
    """Refresh bar_cache for the enabled-strategy universes."""
    try:
        n = quant_jobs.warm_quant_bars()
        logger.info("warmed quant bars: %d rows", n)
    except Exception:
        logger.warning("warm_quant_bars failed", exc_info=True)


def forward_step_all_strategies() -> None:
    """Extend every enabled strategy's equity curve by one day."""
    try:
        summary = quant_jobs.forward_step_all_strategies()
        logger.info("forward_step_all summary: %s", summary)
    except Exception:
        logger.warning("forward_step_all_strategies failed", exc_info=True)
```

In `start_scheduler()`, after the existing `add_job` calls, append:

```python
sched.add_job(warm_quant_bars, "cron", hour=2, minute=30, id="warm_quant_bars",
              max_instances=1, coalesce=True)
sched.add_job(forward_step_all_strategies, "cron", hour=2, minute=45,
              id="forward_step_all_strategies", max_instances=1, coalesce=True)
```

Hours 2:30 / 2:45 UTC ≈ 22:30 / 22:45 ET — well after US market close (16:00 ET) and yfinance has the day's bar.

- [ ] **Step 3: Tests + commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard/.claude/worktrees/quant-lab-q1c/backend && /Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -m pytest tests/test_scheduler.py -v
```
Expect existing scheduler tests still PASS + your new assertion PASS.

Full suite: ~280 (no net new test files, just one new assertion).

```bash
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant/scheduler): wire warm_quant_bars + forward_step_all_strategies

Two new daily cron jobs at 22:30 ET / 22:45 ET (UTC 02:30 / 02:45).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Quant service — `build_overview`

**Files:**
- Create: `backend/app/services/quant_service.py`
- Create: `backend/tests/test_quant_service.py`

Builds the bento home payload: hero combined equity (sum of forward-phase equity across enabled strategies, normalized to $100k), leaderboard rows, recent-trades feed (latest 20), universe-health (bar-cache freshness, last forward-step per strategy).

- [ ] **Step 1: Test**

```python
import json

import pandas as pd
from sqlalchemy import insert

from app.database import (
    bar_cache, get_engine, strategies, strategy_equity, strategy_trades,
)
from app.quant.services_io import build_overview  # we'll alias at top of module


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
```

Note: `build_overview` test imports `from app.quant.services_io import build_overview`. Implementation chooses a module name; either `app.services.quant_service` (matching the existing service pattern) or `app.quant.services_io`. Pick `app.services.quant_service` to match the rest of the project; update test imports accordingly.

- [ ] **Step 2: Implement `app/services/quant_service.py`** with at least `build_overview() -> dict`. See implementation hint:

```python
"""Quant Lab service layer — assembles API payloads from the DB."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import select

from app.database import (
    bar_cache, get_engine, strategies as strategies_t,
    strategy_equity, strategy_runs, strategy_trades,
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
```

- [ ] **Step 3: Tests + commit**

Expect 3 PASS in the new service test file. Full suite: 283.

```bash
git -c commit.gpgsign=false commit -m "feat(quant/service): build_overview — bento home payload"
```

---

## Task 5: Quant service — `build_strategy_detail`

**Files:**
- Modify: `backend/app/services/quant_service.py`
- Modify: `backend/tests/test_quant_service.py`

Builds the detail-page payload for one strategy: metadata + methodology + chosen params + full equity series (each tagged with phase) + drawdown series + monthly returns matrix + tear-sheet metrics + walk-forward windows + parameter sweep + current positions + recent trades (capped at 100).

- [ ] **Step 1: Test**

Add to `backend/tests/test_quant_service.py`:

```python
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
```

- [ ] **Step 2: Implement** in `app/services/quant_service.py`:

```python
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
```

- [ ] **Step 3: Tests + commit**

Expect 5 service-test PASS. Full suite: 285.

```bash
git -c commit.gpgsign=false commit -m "feat(quant/service): build_strategy_detail — drill-down page payload"
```

---

## Task 6: Quant routes — wire everything

**Files:**
- Create: `backend/app/routes/quant.py`
- Create: `backend/tests/test_quant_routes.py`
- Modify: `backend/app/main.py` — `from app.routes.quant import router as quant_router; app.include_router(quant_router)`

Endpoints from the spec:
- `GET /api/quant/overview` → `build_overview`, cached
- `GET /api/quant/strategy/{slug}` → `build_strategy_detail`, cached
- `GET /api/quant/strategy/{slug}/trades?cursor=&limit=` → paginated trade list
- `POST /api/quant/strategy/{slug}/recompute-backtest` → schedule `run_inception_walkforward_async` via BackgroundTasks; returns `202` + `run_id`; `409` if a `pending`/`running` row already exists
- `GET /api/quant/runs/{run_id}` → poll status

All routes auth-gated (existing `require_auth` dependency).

- [ ] **Step 1: Test** (use FastAPI TestClient + the existing auth fixture pattern from `test_finance_routes.py`)

Read `backend/tests/test_finance_routes.py` to see the auth helper pattern. Then write `backend/tests/test_quant_routes.py` with at least these checks:

```python
import json
from sqlalchemy import insert

from app.database import get_engine, strategies, strategy_runs


def test_overview_requires_auth(client):
    resp = client.get("/api/quant/overview")
    assert resp.status_code == 401


def test_overview_returns_payload(client, db, auth_headers):
    resp = client.get("/api/quant/overview", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "leaderboard" in body


def test_strategy_detail_404_when_unknown(client, db, auth_headers):
    resp = client.get("/api/quant/strategy/no-such-thing", headers=auth_headers)
    assert resp.status_code == 404


def test_strategy_detail_returns_payload(client, db, auth_headers):
    with get_engine().begin() as conn:
        conn.execute(insert(strategies).values(
            slug="buy-hold-spy", name="Buy Hold SPY", category="benchmark",
            methodology_blurb="x", universe_kind="spy",
            inception_date="2024-01-02", live_start_date="2025-01-02",
            chosen_params="{}",
            cost_model='{"commission":0,"slippage_bps":5,"allow_short":false}',
            enabled=1, last_forward_step_date=None,
        ))
    resp = client.get("/api/quant/strategy/buy-hold-spy", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["slug"] == "buy-hold-spy"


def test_recompute_backtest_returns_202_run_id(client, db, auth_headers):
    # Seed an enabled strategy.
    with get_engine().begin() as conn:
        conn.execute(insert(strategies).values(
            slug="buy-hold-spy", name="x", category="benchmark",
            methodology_blurb="x", universe_kind="spy",
            inception_date="2024-01-02", live_start_date="2025-01-02",
            chosen_params="{}",
            cost_model='{"commission":0,"slippage_bps":5,"allow_short":false}',
            enabled=1, last_forward_step_date=None,
        ))
    resp = client.post(
        "/api/quant/strategy/buy-hold-spy/recompute-backtest",
        headers=auth_headers,
    )
    assert resp.status_code == 202
    assert "run_id" in resp.json()


def test_recompute_backtest_409_if_in_flight(client, db, auth_headers):
    with get_engine().begin() as conn:
        conn.execute(insert(strategies).values(
            slug="buy-hold-spy", name="x", category="benchmark",
            methodology_blurb="x", universe_kind="spy",
            inception_date="2024-01-02", live_start_date="2025-01-02",
            chosen_params="{}",
            cost_model='{"commission":0,"slippage_bps":5,"allow_short":false}',
            enabled=1, last_forward_step_date=None,
        ))
        conn.execute(insert(strategy_runs).values(
            strategy_slug="buy-hold-spy", run_kind="inception-walkforward",
            started_at="2025-05-22T00:00:00Z", finished_at=None,
            status="running", progress="{}",
            summary_metrics=None, walkforward_windows=None, param_sweep=None,
        ))
    resp = client.post(
        "/api/quant/strategy/buy-hold-spy/recompute-backtest",
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_runs_endpoint_returns_status(client, db, auth_headers):
    with get_engine().begin() as conn:
        rid = conn.execute(insert(strategy_runs).values(
            strategy_slug="buy-hold-spy", run_kind="inception-walkforward",
            started_at="2025-05-22T00:00:00Z", finished_at=None,
            status="running", progress='{"windows_done":1,"windows_total":4}',
            summary_metrics=None, walkforward_windows=None, param_sweep=None,
        )).inserted_primary_key[0]
    resp = client.get(f"/api/quant/runs/{rid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"
```

(The `client`, `db`, and `auth_headers` fixtures already exist in `backend/tests/conftest.py` and/or `test_finance_routes.py` — reuse them. If `auth_headers` isn't a fixture yet, copy the pattern from the existing routes test.)

- [ ] **Step 2: Implement** `backend/app/routes/quant.py`:

```python
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
            started_at="",       # _now_iso set by orchestrator
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
```

- [ ] **Step 3: Wire into main.py**

In `backend/app/main.py`, add the import alongside the existing route imports and `app.include_router(quant_router)` alongside the other includes.

- [ ] **Step 4: Tests + commit**

Expect 7 route tests PASS. Full suite: 292.

```bash
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant/routes): /api/quant/* endpoints — overview + detail + trades + recompute + runs

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Smoke + final commit

Manual sanity check:
- `pytest --tb=no -q` → 292 passing.
- Start the FastAPI app locally and hit `/api/quant/overview` to confirm it returns 401 without auth, 200 with the right token.
- Hit `/api/quant/strategy/buy-hold-spy` and confirm shape.

Fix anything that crops up; small fix commits.

---

## Self-review

- §4.2 forward-step path → Task 1 (runner) + Task 3 (scheduler).
- §7 API surface (overview, detail, trades, recompute-backtest, runs) → Task 6.
- §11 perf budget for daily forward-step → Task 1 returns in well under 60s for the seeded universes; will measure in T7 smoke.
- §12 security: all routes auth-gated via `require_auth` Depends.

No placeholders. All function/property names consistent with Q1a/Q1b conventions.
