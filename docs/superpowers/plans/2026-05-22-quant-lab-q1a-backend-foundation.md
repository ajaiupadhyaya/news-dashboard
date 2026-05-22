# Quant Lab Q1a — Backend Foundation + First 2 Strategies

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Quant Lab backend — bar warehouse, strategy framework, walk-forward engine, cost model, and two starter strategies (`buy-hold-spy`, `sma-crossover`) — wired together so the inception walk-forward orchestrator can run end-to-end on real data and persist real results. No HTTP routes, no scheduler, no frontend in this plan; those land in Q1b/Q1c/Q1d.

**Architecture:** New `backend/app/quant/` package. SQLAlchemy Core `Table` definitions in `backend/app/database.py` (matches existing pattern — not ORM declarative). Strategy ABC + per-strategy modules; `vectorbt` for grid backtests; pure-Python forward-fill simulator that mirrors the same cost model so backtest and (future) forward-step stay numerically consistent. Daily bars only.

**Tech Stack:** Python 3.11+, FastAPI app skeleton (only the package additions in this plan), SQLAlchemy Core, `vectorbt` (new), `quantstats` (new), `yfinance` (existing), pandas, pytest.

**Spec:** `docs/superpowers/specs/2026-05-22-quant-lab-design.md` (Sections 4, 5.1 strategies #1 and #6, 6, 11).

**Out of scope for Q1a (do not implement):**
- HTTP routes (`/api/quant/*`) — Q1c
- APScheduler `warm_bars` / `forward_step_all_strategies` jobs — Q1c
- Forward-step runner (only the `simulate_fills` primitive lands here; the loop is Q1c)
- Strategies #2–5 and #7–9 — Q1b
- Frontend — Q1d

---

## File Map (what gets created vs. modified)

**Modified:**
- `backend/requirements.txt` — add `vectorbt`, `quantstats`
- `backend/app/database.py` — add `bar_cache`, `strategies`, `strategy_runs`, `strategy_equity`, `strategy_trades`, `strategy_positions` Tables (Core style, like existing `ohlcv`, `news_clusters`, etc.)
- `backend/app/models.py` — add Pydantic models the engine and orchestrator pass around

**New:**
- `backend/app/quant/__init__.py`
- `backend/app/quant/universe.py` — S&P 500 constituent list, fixed pair list, helpers
- `backend/app/quant/bars.py` — fetch + cache + read daily bars
- `backend/app/quant/cost_model.py` — `CostModel` dataclass + slippage helpers
- `backend/app/quant/walkforward.py` — window builder + OOS stitcher
- `backend/app/quant/engine.py` — `run_grid`, `run_single`, `simulate_fills`
- `backend/app/quant/strategies/__init__.py`
- `backend/app/quant/strategies/base.py` — `Strategy` ABC, `SignalsResult`, `ParamGrid` types
- `backend/app/quant/strategies/buy_hold_spy.py`
- `backend/app/quant/strategies/sma_crossover.py`
- `backend/app/quant/registry.py` — `STRATEGIES = [...]` + lookup helpers
- `backend/app/quant/orchestration.py` — `inception_walkforward(strategy)` end-to-end
- `backend/tests/test_quant_database.py`
- `backend/tests/test_quant_models.py`
- `backend/tests/test_quant_universe.py`
- `backend/tests/test_quant_bars.py`
- `backend/tests/test_quant_cost_model.py`
- `backend/tests/test_quant_walkforward.py`
- `backend/tests/test_quant_engine.py`
- `backend/tests/test_quant_strategy_buyhold.py`
- `backend/tests/test_quant_strategy_sma.py`
- `backend/tests/test_quant_registry.py`
- `backend/tests/test_quant_orchestration.py`

**Quant tests reuse the existing `db` fixture from `backend/tests/conftest.py` — no new conftest.**

---

## Task 1: Add `vectorbt` + `quantstats` deps

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Append the two new deps**

In `backend/requirements.txt`, append after the existing list:

```
vectorbt>=0.26
quantstats>=0.0.62
```

- [ ] **Step 2: Install into the active env**

Run from `backend/`:
```bash
pip install -r requirements.txt
```
Expected: installs `vectorbt`, `quantstats`, and their transitive deps (`numba`, `llvmlite`, `pyfolio-reloaded`, etc.). This is a heavy install (~150 MB). If `numba` fails to build, install with `pip install numba --upgrade` first.

- [ ] **Step 3: Smoke import**

```bash
python -c "import vectorbt as vbt; import quantstats as qs; print(vbt.__version__, qs.__version__)"
```
Expected: prints two version numbers, no errors.

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "deps(quant): add vectorbt + quantstats for Quant Lab Q1a"
```

---

## Task 2: Add `bar_cache` Table

**Files:**
- Modify: `backend/app/database.py`
- Test: `backend/tests/test_quant_database.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_database.py`:

```python
from datetime import date

from sqlalchemy import insert, select

from app.database import bar_cache, get_engine


def test_bar_cache_insert_and_read(db):
    with get_engine().begin() as conn:
        conn.execute(insert(bar_cache).values(
            symbol="SPY", date="2026-01-02",
            open=470.0, high=472.5, low=469.0, close=471.2, adj_close=471.2,
            volume=80_000_000, source="yfinance",
            fetched_at="2026-01-02T22:00:00Z",
        ))
        row = conn.execute(
            select(bar_cache).where(bar_cache.c.symbol == "SPY")
        ).first()
    assert row.close == 471.2
    assert row.adj_close == 471.2
    assert row.source == "yfinance"


def test_bar_cache_primary_key_is_symbol_date(db):
    with get_engine().begin() as conn:
        conn.execute(insert(bar_cache).values(
            symbol="SPY", date="2026-01-02", open=1, high=1, low=1, close=1,
            adj_close=1, volume=1, source="yfinance", fetched_at="x",
        ))
        # Re-inserting the same (symbol, date) must violate the PK.
        import pytest
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            conn.execute(insert(bar_cache).values(
                symbol="SPY", date="2026-01-02", open=2, high=2, low=2, close=2,
                adj_close=2, volume=2, source="yfinance", fetched_at="x",
            ))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_database.py -v
```
Expected: FAIL — `bar_cache` not importable.

- [ ] **Step 3: Add the Table to database.py**

In `backend/app/database.py`, after the existing `news_clusters` Table and before `_engine: Engine | None = None`, add:

```python
bar_cache = Table(
    "bar_cache", metadata,
    Column("symbol", String(20), primary_key=True),
    Column("date", String(10), primary_key=True),     # ISO yyyy-mm-dd
    Column("open", Float),
    Column("high", Float),
    Column("low", Float),
    Column("close", Float),
    Column("adj_close", Float),
    Column("volume", Integer),
    Column("source", String(20)),                     # "yfinance"
    Column("fetched_at", String(32)),
)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_database.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/database.py backend/tests/test_quant_database.py
git commit -m "feat(quant/db): add bar_cache table"
```

---

## Task 3: Add `strategies` + `strategy_runs` Tables

**Files:**
- Modify: `backend/app/database.py`
- Test: `backend/tests/test_quant_database.py`

- [ ] **Step 1: Extend the failing test**

Append to `backend/tests/test_quant_database.py`:

```python
def test_strategies_row(db):
    from app.database import strategies
    with get_engine().begin() as conn:
        conn.execute(insert(strategies).values(
            slug="buy-hold-spy",
            name="Buy & Hold SPY",
            category="benchmark",
            methodology_blurb="Always long SPY.",
            universe_kind="spy",
            inception_date="2015-01-02",
            live_start_date="2025-01-02",
            chosen_params="{}",                # JSON-encoded
            cost_model='{"commission":0,"slippage_bps":5,"allow_short":false}',
            enabled=1,
            last_forward_step_date=None,
        ))
        row = conn.execute(
            select(strategies).where(strategies.c.slug == "buy-hold-spy")
        ).first()
    assert row.name == "Buy & Hold SPY"
    assert row.universe_kind == "spy"


def test_strategy_runs_row(db):
    from app.database import strategy_runs
    with get_engine().begin() as conn:
        rid = conn.execute(insert(strategy_runs).values(
            strategy_slug="buy-hold-spy",
            run_kind="inception-walkforward",
            started_at="2026-05-22T22:00:00Z",
            finished_at=None,
            status="running",
            progress='{"windows_done":0,"windows_total":8}',
            error=None,
            summary_metrics=None,
            walkforward_windows=None,
            param_sweep=None,
        )).inserted_primary_key[0]
    assert rid is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_database.py -v
```
Expected: FAIL — `strategies` and `strategy_runs` not importable.

- [ ] **Step 3: Add both Tables to database.py**

In `backend/app/database.py`, after the `bar_cache` Table you just added:

```python
strategies = Table(
    "strategies", metadata,
    Column("slug", String(64), primary_key=True),
    Column("name", String(128)),
    Column("category", String(40)),                  # "classic" | "alpha" | "benchmark"
    Column("methodology_blurb", Text),
    Column("universe_kind", String(32)),             # "spy" | "sp500" | "pairs-fixed" | "news-top100"
    Column("inception_date", String(10)),            # ISO
    Column("live_start_date", String(10)),           # ISO
    Column("chosen_params", Text),                   # JSON
    Column("cost_model", Text),                      # JSON {commission, slippage_bps, allow_short}
    Column("enabled", Integer),                      # 0/1
    Column("last_forward_step_date", String(10)),    # ISO, nullable
)

strategy_runs = Table(
    "strategy_runs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("strategy_slug", String(64), index=True),
    Column("run_kind", String(40)),                  # "inception-walkforward" | "param-sweep"
    Column("started_at", String(32)),
    Column("finished_at", String(32)),               # nullable
    Column("status", String(16)),                    # "pending"|"running"|"success"|"failed"
    Column("progress", Text),                        # JSON {windows_done, windows_total}
    Column("error", Text),                           # nullable
    Column("summary_metrics", Text),                 # JSON, nullable
    Column("walkforward_windows", Text),             # JSON, nullable
    Column("param_sweep", Text),                     # JSON, nullable
)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_database.py -v
```
Expected: PASS (4 tests now).

- [ ] **Step 5: Commit**

```bash
git add backend/app/database.py backend/tests/test_quant_database.py
git commit -m "feat(quant/db): add strategies + strategy_runs tables"
```

---

## Task 4: Add `strategy_equity` + `strategy_trades` + `strategy_positions` Tables

**Files:**
- Modify: `backend/app/database.py`
- Test: `backend/tests/test_quant_database.py`

- [ ] **Step 1: Extend the failing test**

Append to `backend/tests/test_quant_database.py`:

```python
def test_strategy_equity_pk_is_slug_date(db):
    from app.database import strategy_equity
    import pytest
    from sqlalchemy.exc import IntegrityError
    with get_engine().begin() as conn:
        conn.execute(insert(strategy_equity).values(
            strategy_slug="buy-hold-spy", date="2026-01-02",
            equity=100_000.0, cash=0.0,
            gross_exposure=100_000.0, net_exposure=100_000.0,
            daily_return=0.0, phase="forward",
        ))
        with pytest.raises(IntegrityError):
            conn.execute(insert(strategy_equity).values(
                strategy_slug="buy-hold-spy", date="2026-01-02",
                equity=99_000.0, cash=0.0,
                gross_exposure=99_000.0, net_exposure=99_000.0,
                daily_return=-0.01, phase="forward",
            ))


def test_strategy_trades_round_trip(db):
    from app.database import strategy_trades
    with get_engine().begin() as conn:
        tid = conn.execute(insert(strategy_trades).values(
            strategy_slug="sma-crossover", date="2026-01-02", symbol="SPY",
            side="buy", qty=100, price=471.5, commission=0.0,
            notional=47_150.0, phase="forward",
        )).inserted_primary_key[0]
        row = conn.execute(
            select(strategy_trades).where(strategy_trades.c.id == tid)
        ).first()
    assert row.symbol == "SPY"
    assert row.side == "buy"
    assert row.qty == 100


def test_strategy_positions_pk_is_slug_symbol(db):
    from app.database import strategy_positions
    import pytest
    from sqlalchemy.exc import IntegrityError
    with get_engine().begin() as conn:
        conn.execute(insert(strategy_positions).values(
            strategy_slug="buy-hold-spy", symbol="SPY",
            qty=210, avg_cost=470.5,
            opened_at="2025-01-02", last_marked_at="2026-01-02",
        ))
        with pytest.raises(IntegrityError):
            conn.execute(insert(strategy_positions).values(
                strategy_slug="buy-hold-spy", symbol="SPY",
                qty=1, avg_cost=1.0,
                opened_at="x", last_marked_at="x",
            ))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_database.py -v
```
Expected: FAIL — the three new Tables aren't importable.

- [ ] **Step 3: Add the three Tables**

In `backend/app/database.py`, after `strategy_runs`:

```python
strategy_equity = Table(
    "strategy_equity", metadata,
    Column("strategy_slug", String(64), primary_key=True),
    Column("date", String(10), primary_key=True),
    Column("equity", Float),
    Column("cash", Float),
    Column("gross_exposure", Float),
    Column("net_exposure", Float),
    Column("daily_return", Float),
    Column("phase", String(10)),                     # "backtest" | "forward"
)

strategy_trades = Table(
    "strategy_trades", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("strategy_slug", String(64), index=True),
    Column("date", String(10), index=True),
    Column("symbol", String(20)),
    Column("side", String(10)),                      # "buy"|"sell"|"short"|"cover"
    Column("qty", Integer),
    Column("price", Float),
    Column("commission", Float),
    Column("notional", Float),
    Column("phase", String(10)),
)

strategy_positions = Table(
    "strategy_positions", metadata,
    Column("strategy_slug", String(64), primary_key=True),
    Column("symbol", String(20), primary_key=True),
    Column("qty", Integer),
    Column("avg_cost", Float),
    Column("opened_at", String(10)),
    Column("last_marked_at", String(10)),
)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_database.py -v
```
Expected: PASS (7 tests now).

- [ ] **Step 5: Commit**

```bash
git add backend/app/database.py backend/tests/test_quant_database.py
git commit -m "feat(quant/db): add strategy_equity, strategy_trades, strategy_positions tables"
```

---

## Task 5: Pydantic models for the Quant Lab

**Files:**
- Modify: `backend/app/models.py`
- Test: `backend/tests/test_quant_models.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_models.py`:

```python
from app.models import (
    StrategyMeta, EquityPoint, TradeRecord, WalkforwardWindow,
    ParameterSweepCell, RunStatus, CostModelSchema, TearSheetMetrics,
)


def test_strategy_meta_constructs():
    m = StrategyMeta(
        slug="buy-hold-spy", name="Buy & Hold SPY",
        category="benchmark", methodology_blurb="Always long SPY.",
        universe_kind="spy", inception_date="2015-01-02",
        live_start_date="2025-01-02",
        chosen_params={}, enabled=True,
    )
    assert m.slug == "buy-hold-spy"
    assert m.enabled is True


def test_equity_point_phases():
    p = EquityPoint(date="2026-01-02", equity=100_000.0, cash=0.0,
                    gross_exposure=100_000.0, net_exposure=100_000.0,
                    daily_return=0.0, phase="backtest")
    assert p.phase == "backtest"


def test_trade_record_basic():
    t = TradeRecord(date="2026-01-02", symbol="SPY", side="buy",
                    qty=100, price=471.5, commission=0.0,
                    notional=47_150.0, phase="forward")
    assert t.side == "buy"


def test_walkforward_window_metrics():
    w = WalkforwardWindow(
        train_start="2015-01-02", train_end="2017-12-29",
        test_start="2018-01-02", test_end="2018-12-31",
        chosen_params={"fast": 20, "slow": 100},
        oos_metrics={"sharpe": 0.42, "cagr": 0.07},
    )
    assert w.oos_metrics["sharpe"] == 0.42


def test_parameter_sweep_cell():
    c = ParameterSweepCell(params={"fast": 20, "slow": 100}, sharpe=0.7)
    assert c.params["fast"] == 20


def test_run_status_enum_values():
    s = RunStatus(status="running", progress={"windows_done": 1, "windows_total": 8},
                  error=None)
    assert s.status == "running"


def test_cost_model_schema_defaults():
    c = CostModelSchema()  # all defaults
    assert c.commission == 0.0
    assert c.slippage_bps == 5.0
    assert c.allow_short is False


def test_tear_sheet_metrics_fields():
    t = TearSheetMetrics(total_return=0.34, cagr=0.07, sharpe=0.9,
                         sortino=1.2, calmar=0.5, max_drawdown=-0.18,
                         win_rate=0.55, volatility=0.16)
    assert t.cagr == 0.07
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_models.py -v
```
Expected: FAIL — imports don't exist.

- [ ] **Step 3: Add Pydantic models**

Append to `backend/app/models.py`:

```python
# ---- Quant Lab ----
from typing import Literal


class CostModelSchema(BaseModel):
    commission: float = 0.0
    slippage_bps: float = 5.0
    allow_short: bool = False


class StrategyMeta(BaseModel):
    slug: str
    name: str
    category: Literal["classic", "alpha", "benchmark"]
    methodology_blurb: str
    universe_kind: Literal["spy", "sp500", "pairs-fixed", "news-top100"]
    inception_date: str
    live_start_date: str
    chosen_params: dict
    cost_model: CostModelSchema = CostModelSchema()
    enabled: bool = True
    last_forward_step_date: str | None = None


class EquityPoint(BaseModel):
    date: str
    equity: float
    cash: float
    gross_exposure: float
    net_exposure: float
    daily_return: float
    phase: Literal["backtest", "forward"]


class TradeRecord(BaseModel):
    date: str
    symbol: str
    side: Literal["buy", "sell", "short", "cover"]
    qty: int
    price: float
    commission: float
    notional: float
    phase: Literal["backtest", "forward"]


class WalkforwardWindow(BaseModel):
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    chosen_params: dict
    oos_metrics: dict[str, float]


class ParameterSweepCell(BaseModel):
    params: dict
    sharpe: float


class RunStatus(BaseModel):
    status: Literal["pending", "running", "success", "failed"]
    progress: dict[str, int]   # {windows_done, windows_total}
    error: str | None = None


class TearSheetMetrics(BaseModel):
    total_return: float
    cagr: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    win_rate: float
    volatility: float
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_models.py -v
```
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_quant_models.py
git commit -m "feat(quant): add Pydantic models for strategy metadata, equity, trades, walk-forward"
```

---

## Task 6: Universe module

**Files:**
- Create: `backend/app/quant/__init__.py`
- Create: `backend/app/quant/universe.py`
- Test: `backend/tests/test_quant_universe.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_universe.py`:

```python
from app.quant.universe import (
    SP500_SYMBOLS, PAIRS, get_universe, list_universe_kinds,
)


def test_sp500_symbols_is_a_nonempty_list_of_strings():
    assert isinstance(SP500_SYMBOLS, tuple)
    assert len(SP500_SYMBOLS) >= 480       # allow some drift over time
    assert all(isinstance(s, str) and s.isupper() for s in SP500_SYMBOLS)
    assert "AAPL" in SP500_SYMBOLS
    assert "MSFT" in SP500_SYMBOLS
    assert "SPY" not in SP500_SYMBOLS      # SPY is the ETF, not in S&P 500 itself


def test_pairs_are_well_formed():
    assert isinstance(PAIRS, tuple)
    assert len(PAIRS) == 5
    for a, b in PAIRS:
        assert isinstance(a, str) and isinstance(b, str)
        assert a != b


def test_get_universe_spy():
    assert get_universe("spy") == ("SPY",)


def test_get_universe_sp500():
    u = get_universe("sp500")
    assert isinstance(u, tuple)
    assert "AAPL" in u


def test_get_universe_pairs_fixed():
    u = get_universe("pairs-fixed")
    # All unique symbols from the 5 pairs
    assert "KO" in u and "PEP" in u and "GOOG" in u and "META" in u


def test_get_universe_unknown_raises():
    import pytest
    with pytest.raises(ValueError):
        get_universe("not-a-real-universe-kind")


def test_list_universe_kinds():
    kinds = list_universe_kinds()
    assert set(kinds) == {"spy", "sp500", "pairs-fixed", "news-top100"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_universe.py -v
```
Expected: FAIL — `app.quant.universe` doesn't exist.

- [ ] **Step 3: Create the package + universe module**

Create empty `backend/app/quant/__init__.py`:

```python
```

Create `backend/app/quant/universe.py`. The S&P 500 list is a static snapshot — fine for Q1; refreshing it is out of scope. Use the constituent list pasted below (current as of 2026-05-22; trimmed to fit, ~500 names):

```python
"""Universe definitions for Quant Lab strategies.

The S&P 500 list is a static snapshot. Refresh procedure is documented
in docs/superpowers/specs/2026-05-22-quant-lab-design.md §4 (out of
scope for Q1a; we revisit when delisted names start producing missing-
bar warnings in the forward-step logs).
"""

# Static snapshot of S&P 500 constituents (excluding the SPY ETF itself).
# Source: Wikipedia S&P 500 list as of 2026-05-22.
SP500_SYMBOLS: tuple[str, ...] = (
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "BRK-B",
    "LLY", "JPM", "V", "XOM", "UNH", "MA", "COST", "HD", "PG", "JNJ", "ABBV",
    "NFLX", "BAC", "KO", "CRM", "CVX", "MRK", "AMD", "PEP", "WMT", "ADBE",
    "ORCL", "TMO", "ACN", "MCD", "CSCO", "ABT", "QCOM", "DIS", "WFC", "INTC",
    # … (paste the rest of the S&P 500 here; engineer: pull from
    # https://en.wikipedia.org/wiki/List_of_S%26P_500_companies — the
    # `Symbol` column — and append all remaining tickers, sorted by
    # market cap descending if convenient. Normalize "BRK.B" → "BRK-B"
    # and "BF.B" → "BF-B" for yfinance compatibility.)
)

# Fixed pair list for `pairs-trading` strategy. Cointegrated historical pairs.
PAIRS: tuple[tuple[str, str], ...] = (
    ("KO", "PEP"),
    ("MA", "V"),
    ("GOOG", "META"),
    ("XOM", "CVX"),
    ("JPM", "BAC"),
)

# Universe-kind enum mapped to symbol tuples. `news-top100` is computed
# dynamically by the news-sentiment strategy at runtime (lands in Q1b);
# we return a placeholder here so the registry validates.
_UNIVERSE_KINDS = ("spy", "sp500", "pairs-fixed", "news-top100")


def list_universe_kinds() -> tuple[str, ...]:
    return _UNIVERSE_KINDS


def get_universe(kind: str) -> tuple[str, ...]:
    if kind == "spy":
        return ("SPY",)
    if kind == "sp500":
        return SP500_SYMBOLS
    if kind == "pairs-fixed":
        symbols: set[str] = set()
        for a, b in PAIRS:
            symbols.add(a); symbols.add(b)
        return tuple(sorted(symbols))
    if kind == "news-top100":
        # Resolved at runtime by the news-sentiment strategy (Q1b).
        # Q1a returns the first 100 S&P 500 names as a stable placeholder.
        return SP500_SYMBOLS[:100]
    raise ValueError(f"Unknown universe kind: {kind}")
```

**Note to implementer:** for the S&P 500 paste-in, ensure ≥ 480 symbols so `test_sp500_symbols_is_a_nonempty_list_of_strings` passes. Normalize Berkshire (`BRK.B` → `BRK-B`) and Brown-Forman (`BF.B` → `BF-B`) so yfinance accepts them. The list does NOT need to be exhaustive — 480+ liquid names is sufficient for Q1.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_universe.py -v
```
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/quant/__init__.py backend/app/quant/universe.py backend/tests/test_quant_universe.py
git commit -m "feat(quant): add universe module — S&P 500 snapshot + fixed pairs"
```

---

## Task 7: Bars module — fetch + cache + read

**Files:**
- Create: `backend/app/quant/bars.py`
- Test: `backend/tests/test_quant_bars.py`

The bars module is the warehouse: it pulls daily OHLCV via yfinance, upserts to `bar_cache`, and serves DataFrames keyed `(date, symbol)`. Idempotent on `(symbol, date)`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_bars.py`:

```python
from datetime import date
from unittest.mock import patch

import pandas as pd
from sqlalchemy import select

from app.database import bar_cache, get_engine
from app.quant.bars import upsert_bars, load_bars, get_cached_dates


def _fake_yf_df(symbol: str, start: str, end: str) -> pd.DataFrame:
    idx = pd.date_range(start=start, end=end, freq="B")
    return pd.DataFrame({
        "Open":      [100.0 + i for i in range(len(idx))],
        "High":      [101.0 + i for i in range(len(idx))],
        "Low":       [ 99.0 + i for i in range(len(idx))],
        "Close":     [100.5 + i for i in range(len(idx))],
        "Adj Close": [100.5 + i for i in range(len(idx))],
        "Volume":    [1_000_000 for _ in range(len(idx))],
    }, index=idx)


def test_upsert_bars_writes_to_cache(db):
    df = _fake_yf_df("SPY", "2026-01-02", "2026-01-09")
    upsert_bars("SPY", df)
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(bar_cache).where(bar_cache.c.symbol == "SPY")
        ).all()
    assert len(rows) == len(df)
    # Spot check the first row.
    first = rows[0]
    assert first.symbol == "SPY"
    assert first.close == df.iloc[0]["Close"]


def test_upsert_bars_is_idempotent(db):
    df = _fake_yf_df("SPY", "2026-01-02", "2026-01-09")
    upsert_bars("SPY", df)
    upsert_bars("SPY", df)   # re-run — must NOT duplicate rows
    with get_engine().begin() as conn:
        n = conn.execute(
            select(bar_cache).where(bar_cache.c.symbol == "SPY")
        ).all()
    assert len(n) == len(df)


def test_upsert_bars_updates_existing_row_when_close_changes(db):
    df = _fake_yf_df("SPY", "2026-01-02", "2026-01-09")
    upsert_bars("SPY", df)
    # Simulate yfinance returning a corrected adj_close
    df2 = df.copy()
    df2["Adj Close"] = df2["Adj Close"] + 0.5
    upsert_bars("SPY", df2)
    with get_engine().begin() as conn:
        row = conn.execute(
            select(bar_cache).where(
                (bar_cache.c.symbol == "SPY")
                & (bar_cache.c.date == df.index[0].strftime("%Y-%m-%d"))
            )
        ).first()
    assert row.adj_close == df2.iloc[0]["Adj Close"]


def test_load_bars_returns_long_dataframe(db):
    upsert_bars("SPY", _fake_yf_df("SPY", "2026-01-02", "2026-01-09"))
    upsert_bars("AAPL", _fake_yf_df("AAPL", "2026-01-02", "2026-01-09"))
    df = load_bars(["SPY", "AAPL"], start="2026-01-02", end="2026-01-09")
    # Columns: date, symbol, open, high, low, close, adj_close, volume
    assert set(df.columns) >= {"date", "symbol", "open", "high", "low",
                               "close", "adj_close", "volume"}
    assert set(df["symbol"].unique()) == {"SPY", "AAPL"}


def test_load_bars_pivot_close_helper(db):
    upsert_bars("SPY", _fake_yf_df("SPY", "2026-01-02", "2026-01-09"))
    upsert_bars("AAPL", _fake_yf_df("AAPL", "2026-01-02", "2026-01-09"))
    from app.quant.bars import load_close_matrix
    wide = load_close_matrix(["SPY", "AAPL"], start="2026-01-02", end="2026-01-09")
    # rows = dates, columns = symbols, values = adj_close
    assert list(wide.columns) == ["AAPL", "SPY"]
    assert wide.shape[0] == 6   # 6 business days Jan 2–9 2026


def test_get_cached_dates_returns_set(db):
    upsert_bars("SPY", _fake_yf_df("SPY", "2026-01-02", "2026-01-09"))
    d = get_cached_dates("SPY")
    assert "2026-01-02" in d
    assert isinstance(d, set)


def test_fetch_and_cache_uses_yfinance_when_missing(db):
    """fetch_and_cache should call yfinance only for missing dates."""
    from app.quant.bars import fetch_and_cache
    with patch("app.quant.bars._download_yf") as mocked:
        mocked.return_value = _fake_yf_df("SPY", "2026-01-02", "2026-01-09")
        fetch_and_cache(["SPY"], start="2026-01-02", end="2026-01-09")
        assert mocked.called
    # Second call should hit the cache and NOT re-download (start/end cover same range).
    with patch("app.quant.bars._download_yf") as mocked:
        fetch_and_cache(["SPY"], start="2026-01-02", end="2026-01-09")
        assert not mocked.called
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_bars.py -v
```
Expected: FAIL — `app.quant.bars` does not exist.

- [ ] **Step 3: Implement `bars.py`**

Create `backend/app/quant/bars.py`:

```python
"""Daily-bar warehouse for Quant Lab.

- `upsert_bars(symbol, df)`: idempotent write of a yfinance-shaped DataFrame
  into `bar_cache`. (symbol, date) is the PK; existing rows are replaced.
- `load_bars(symbols, start, end)`: long DataFrame from cache.
- `load_close_matrix(symbols, start, end)`: wide DataFrame (date × symbol)
  of adj_close, ready for vectorbt.
- `fetch_and_cache(symbols, start, end)`: top-level — checks the cache,
  downloads any missing date ranges per symbol via yfinance, upserts.
- `get_cached_dates(symbol)`: set of ISO dates already in cache.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf
from sqlalchemy import delete, insert, select

from app.database import bar_cache, get_engine

logger = logging.getLogger(__name__)


def _download_yf(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    """Thin wrapper around yfinance — split out for ease of mocking in tests."""
    return yf.download(
        tickers=symbols,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="ticker" if len(symbols) > 1 else "column",
        threads=True,
    )


def upsert_bars(symbol: str, df: pd.DataFrame) -> int:
    """Replace cached rows for `symbol` on every date in `df`.

    `df` is expected to be a yfinance-shaped DataFrame indexed by Timestamp
    with columns Open, High, Low, Close, Adj Close, Volume.
    Returns the number of rows written.
    """
    if df is None or df.empty:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    dates = [ts.strftime("%Y-%m-%d") for ts in df.index]
    rows = [
        {
            "symbol": symbol,
            "date": d,
            "open": float(df.iloc[i]["Open"]),
            "high": float(df.iloc[i]["High"]),
            "low": float(df.iloc[i]["Low"]),
            "close": float(df.iloc[i]["Close"]),
            "adj_close": float(df.iloc[i]["Adj Close"]),
            "volume": int(df.iloc[i]["Volume"]),
            "source": "yfinance",
            "fetched_at": now,
        }
        for i, d in enumerate(dates)
    ]
    with get_engine().begin() as conn:
        conn.execute(
            delete(bar_cache).where(
                (bar_cache.c.symbol == symbol)
                & (bar_cache.c.date.in_(dates))
            )
        )
        conn.execute(insert(bar_cache), rows)
    return len(rows)


def load_bars(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    """Long-format DataFrame of cached bars."""
    with get_engine().begin() as conn:
        result = conn.execute(
            select(bar_cache).where(
                bar_cache.c.symbol.in_(symbols)
                & (bar_cache.c.date >= start)
                & (bar_cache.c.date <= end)
            ).order_by(bar_cache.c.symbol, bar_cache.c.date)
        )
        rows = [dict(r._mapping) for r in result]
    if not rows:
        return pd.DataFrame(columns=[
            "date", "symbol", "open", "high", "low",
            "close", "adj_close", "volume", "source", "fetched_at",
        ])
    return pd.DataFrame(rows)


def load_close_matrix(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    """Wide DataFrame: rows = trading dates, columns = symbols, values = adj_close."""
    long = load_bars(symbols, start, end)
    if long.empty:
        return pd.DataFrame()
    wide = long.pivot(index="date", columns="symbol", values="adj_close")
    wide.index = pd.to_datetime(wide.index)
    wide = wide.sort_index().sort_index(axis=1)
    return wide


def get_cached_dates(symbol: str) -> set[str]:
    with get_engine().begin() as conn:
        result = conn.execute(
            select(bar_cache.c.date).where(bar_cache.c.symbol == symbol)
        )
        return {r[0] for r in result}


def fetch_and_cache(symbols: list[str], start: str, end: str) -> int:
    """Fill the cache for [start, end] across `symbols`. Downloads only when
    the cached coverage is missing the requested range for a symbol.

    Returns the number of rows written.
    """
    # Crude: for each symbol, if any business day in [start, end] is missing,
    # we redownload that symbol's whole range. Sufficient for Q1a; a per-symbol
    # gap-aware fetch is a later optimization.
    business_days = {ts.strftime("%Y-%m-%d") for ts in pd.bdate_range(start, end)}
    symbols_to_fetch = [
        s for s in symbols
        if not business_days.issubset(get_cached_dates(s))
    ]
    if not symbols_to_fetch:
        return 0

    written = 0
    # yfinance batches up to ~50 symbols cleanly
    CHUNK = 50
    for i in range(0, len(symbols_to_fetch), CHUNK):
        chunk = symbols_to_fetch[i:i + CHUNK]
        df = _download_yf(chunk, start=start, end=end)
        if df is None or df.empty:
            logger.warning("yfinance returned empty for chunk %s", chunk)
            continue
        for sym in chunk:
            try:
                sub = df[sym] if len(chunk) > 1 else df
                if sub is None or sub.empty:
                    continue
                # Drop any rows with NaN Close (e.g., halted day)
                sub = sub.dropna(subset=["Close", "Adj Close"])
                written += upsert_bars(sym, sub)
            except (KeyError, AttributeError):
                logger.warning("no data returned for %s in chunk %s", sym, chunk)
                continue
    return written
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_bars.py -v
```
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/quant/bars.py backend/tests/test_quant_bars.py
git commit -m "feat(quant): bars warehouse — yfinance fetch + idempotent cache + wide loader"
```

---

## Task 8: Cost model

**Files:**
- Create: `backend/app/quant/cost_model.py`
- Test: `backend/tests/test_quant_cost_model.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_cost_model.py`:

```python
from app.quant.cost_model import CostModel, apply_slippage


def test_default_cost_model_is_alpaca_style():
    c = CostModel()
    assert c.commission == 0.0
    assert c.slippage_bps == 5.0
    assert c.allow_short is False


def test_apply_slippage_buy_pushes_price_up():
    px = apply_slippage(100.0, side="buy", slippage_bps=5)
    # 5 bps = 0.05% = +0.05 on 100.00
    assert px == 100.05


def test_apply_slippage_sell_pushes_price_down():
    px = apply_slippage(100.0, side="sell", slippage_bps=5)
    assert px == 99.95


def test_apply_slippage_short_is_like_sell():
    assert apply_slippage(100.0, side="short", slippage_bps=10) == 99.9


def test_apply_slippage_cover_is_like_buy():
    assert apply_slippage(100.0, side="cover", slippage_bps=10) == 100.1


def test_apply_slippage_zero_bps_returns_input():
    assert apply_slippage(123.45, side="buy", slippage_bps=0) == 123.45


def test_cost_model_serializes_to_dict():
    c = CostModel(commission=0.0, slippage_bps=5.0, allow_short=True)
    assert c.to_dict() == {"commission": 0.0, "slippage_bps": 5.0, "allow_short": True}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_cost_model.py -v
```
Expected: FAIL.

- [ ] **Step 3: Implement `cost_model.py`**

Create `backend/app/quant/cost_model.py`:

```python
"""Uniform cost model used by both the backtest engine and the (future)
forward-step runner — keeps the two paths numerically consistent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    commission: float = 0.0          # dollars per fill
    slippage_bps: float = 5.0        # basis points, per side
    allow_short: bool = False

    def to_dict(self) -> dict:
        return {
            "commission": self.commission,
            "slippage_bps": self.slippage_bps,
            "allow_short": self.allow_short,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CostModel":
        return cls(
            commission=float(d.get("commission", 0.0)),
            slippage_bps=float(d.get("slippage_bps", 5.0)),
            allow_short=bool(d.get("allow_short", False)),
        )


def apply_slippage(price: float, *, side: str, slippage_bps: float) -> float:
    """Push price adverse-to-trader by `slippage_bps` basis points.

    buys / covers fill above mid; sells / shorts fill below mid.
    """
    if slippage_bps == 0:
        return price
    mult = slippage_bps / 10_000.0
    if side in ("buy", "cover"):
        return round(price * (1 + mult), 6)
    if side in ("sell", "short"):
        return round(price * (1 - mult), 6)
    raise ValueError(f"Unknown side: {side}")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_cost_model.py -v
```
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/quant/cost_model.py backend/tests/test_quant_cost_model.py
git commit -m "feat(quant): cost model — uniform slippage + commission shared by backtest + forward"
```

---

## Task 9: Walk-forward window builder + OOS stitcher

**Files:**
- Create: `backend/app/quant/walkforward.py`
- Test: `backend/tests/test_quant_walkforward.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_walkforward.py`:

```python
from datetime import date

import pandas as pd

from app.quant.walkforward import build_walkforward_windows, stitch_oos_equity


def test_build_windows_basic_3y_train_1y_test_6mo_step():
    dates = pd.date_range("2015-01-02", "2024-12-31", freq="B")
    windows = build_walkforward_windows(
        dates, train_years=3, test_years=1, step_months=6,
    )
    # First window: train 2015-01-02 → 2017-12-31, test 2018-01-02 → 2018-12-31
    assert windows[0].train_start == "2015-01-02"
    assert windows[0].train_end >= "2017-12-29"
    assert windows[0].test_start >= "2018-01-02"
    assert windows[0].test_end >= "2018-12-29"
    # Subsequent windows step forward by 6 months.
    second_test_start = windows[1].test_start
    assert second_test_start >= "2018-06-29"
    # Last window's test_end should be within the last calendar year.
    assert windows[-1].test_end <= "2024-12-31"


def test_build_windows_skips_when_insufficient_data():
    dates = pd.date_range("2024-01-02", "2024-06-30", freq="B")  # 6 months only
    windows = build_walkforward_windows(
        dates, train_years=3, test_years=1, step_months=6,
    )
    assert windows == []


def test_stitch_oos_equity_concatenates_test_segments():
    # Two windows: each has an OOS equity Series indexed by date.
    s1 = pd.Series(
        [100_000, 101_000, 102_000],
        index=pd.to_datetime(["2018-01-02", "2018-01-03", "2018-01-04"]),
    )
    s2 = pd.Series(
        # NB: stitcher should rescale s2 to start where s1 ended.
        [100_000, 99_000, 101_000],
        index=pd.to_datetime(["2018-01-05", "2018-01-08", "2018-01-09"]),
    )
    stitched = stitch_oos_equity([s1, s2])
    # First point preserved.
    assert stitched.iloc[0] == 100_000
    # Stitching: s2 starts at 102_000 (where s1 ended) and applies its returns
    assert round(stitched.iloc[-1], 2) == round(102_000 * (101_000 / 100_000), 2)


def test_stitch_oos_equity_handles_overlap_by_keeping_first_window():
    s1 = pd.Series(
        [100_000, 101_000],
        index=pd.to_datetime(["2018-01-02", "2018-01-03"]),
    )
    s2 = pd.Series(
        [100_000, 102_000, 103_000],
        index=pd.to_datetime(["2018-01-03", "2018-01-04", "2018-01-05"]),
    )
    stitched = stitch_oos_equity([s1, s2])
    # Date 2018-01-03 should come from s1, not s2.
    assert stitched.loc["2018-01-03"] == 101_000


def test_stitch_oos_equity_empty_returns_empty():
    out = stitch_oos_equity([])
    assert out.empty
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_walkforward.py -v
```
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement `walkforward.py`**

Create `backend/app/quant/walkforward.py`:

```python
"""Walk-forward windows + OOS equity stitching.

A walk-forward analysis splits a long time series into rolling
(train, test) windows: parameters are optimized on `train` then evaluated
out-of-sample on `test`. The OOS equity from each test window is stitched
together to form the displayed "backtest" equity curve — every point is
out-of-sample so the curve is not in-sample fit.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from dateutil.relativedelta import relativedelta


@dataclass(frozen=True)
class Window:
    train_start: str   # ISO yyyy-mm-dd
    train_end: str
    test_start: str
    test_end: str


def build_walkforward_windows(
    dates: pd.DatetimeIndex,
    *,
    train_years: int,
    test_years: int,
    step_months: int,
) -> list[Window]:
    """Return all walk-forward windows that fit inside `dates`."""
    if len(dates) == 0:
        return []
    first = dates[0]
    last = dates[-1]
    windows: list[Window] = []

    train_start = first
    while True:
        train_end = train_start + relativedelta(years=train_years) - relativedelta(days=1)
        test_start = train_end + relativedelta(days=1)
        test_end = test_start + relativedelta(years=test_years) - relativedelta(days=1)
        if test_end > last:
            break

        # Snap to actual trading dates contained in `dates`.
        ts = dates[(dates >= train_start) & (dates <= train_end)]
        te = dates[(dates >= test_start) & (dates <= test_end)]
        if len(ts) == 0 or len(te) == 0:
            train_start += relativedelta(months=step_months)
            continue
        windows.append(Window(
            train_start=ts[0].strftime("%Y-%m-%d"),
            train_end=ts[-1].strftime("%Y-%m-%d"),
            test_start=te[0].strftime("%Y-%m-%d"),
            test_end=te[-1].strftime("%Y-%m-%d"),
        ))
        train_start += relativedelta(months=step_months)
    return windows


def stitch_oos_equity(segments: list[pd.Series]) -> pd.Series:
    """Stitch per-window OOS equity series into a single continuous equity curve.

    Each segment is rescaled to start at the previous segment's last value,
    so the resulting curve compounds returns across windows.
    Overlapping dates are resolved by keeping the earlier window's value.
    """
    if not segments:
        return pd.Series(dtype="float64")

    # First segment carried as-is.
    out: pd.Series = segments[0].copy()
    for seg in segments[1:]:
        if seg.empty:
            continue
        new = seg[~seg.index.isin(out.index)]
        if new.empty:
            continue
        last_existing = out.iloc[-1]
        first_seg = seg.iloc[0]
        if first_seg == 0:
            continue
        rescaled = new * (last_existing / first_seg)
        out = pd.concat([out, rescaled])
    return out.sort_index()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_walkforward.py -v
```
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/quant/walkforward.py backend/tests/test_quant_walkforward.py
git commit -m "feat(quant): walk-forward window builder + OOS equity stitcher"
```

---

## Task 10: Strategy base class

**Files:**
- Create: `backend/app/quant/strategies/__init__.py`
- Create: `backend/app/quant/strategies/base.py`

- [ ] **Step 1: Create the package + base module**

Create empty `backend/app/quant/strategies/__init__.py`:

```python
```

Create `backend/app/quant/strategies/base.py`:

```python
"""Strategy base class + result types.

Every strategy is a subclass that implements `generate_signals(bars, params)`
returning a DataFrame of entry/exit flags (or target-weight floats) keyed
by (date, symbol). The engine handles portfolio construction + costs
uniformly so individual strategies stay focused on signal logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


# A parameter grid is a dict of param-name -> list-of-values. The engine
# takes the Cartesian product to generate all combinations for the sweep.
ParamGrid = dict[str, list[Any]]


@dataclass
class StrategyContext:
    """Per-call context passed to `generate_signals`.

    Lets strategies that read auxiliary data (news, FRED, fundamentals)
    receive it without changing the base signature. Q1a strategies don't
    use any of these; populated by Q1b dashboard-integrated strategies.
    """
    news_clusters: pd.DataFrame | None = None
    econ_series: dict[str, pd.Series] = field(default_factory=dict)
    fundamentals: dict[str, dict] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategySpec:
    """Metadata declared by a Strategy subclass."""
    slug: str
    name: str
    category: str                # "classic" | "alpha" | "benchmark"
    universe_kind: str
    inception_date: str
    live_start_date: str
    methodology_blurb: str
    allow_short: bool = False    # only `pairs-trading` will set True


class Strategy(ABC):
    spec: StrategySpec
    sweep_grid: ParamGrid

    @abstractmethod
    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        """Return a DataFrame of target weights, indexed by date with one
        column per symbol. NaN / 0 means flat; positive = long share of
        portfolio; negative = short (only meaningful when allow_short=True).

        Engine convention: weights at row `t` are the **target portfolio at
        the close of day t**, executed on day t's close price.
        """
        ...
```

- [ ] **Step 2: Smoke import**

```bash
cd backend && python -c "from app.quant.strategies.base import Strategy, StrategySpec, StrategyContext, ParamGrid; print('ok')"
```
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/quant/strategies/__init__.py backend/app/quant/strategies/base.py
git commit -m "feat(quant): strategy ABC + spec + context types"
```

---

## Task 11: Strategy — `buy-hold-spy`

**Files:**
- Create: `backend/app/quant/strategies/buy_hold_spy.py`
- Test: `backend/tests/test_quant_strategy_buyhold.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_strategy_buyhold.py`:

```python
import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.buy_hold_spy import BuyHoldSPY


def test_metadata():
    s = BuyHoldSPY()
    assert s.spec.slug == "buy-hold-spy"
    assert s.spec.category == "benchmark"
    assert s.spec.universe_kind == "spy"
    assert s.sweep_grid == {}


def test_generate_signals_returns_full_long_weight():
    s = BuyHoldSPY()
    bars = pd.DataFrame(
        {"SPY": [100.0, 101.0, 102.0]},
        index=pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-04"]),
    )
    weights = s.generate_signals(bars, params={}, ctx=StrategyContext())
    assert list(weights.columns) == ["SPY"]
    assert (weights["SPY"] == 1.0).all()


def test_generate_signals_skips_leading_nan():
    s = BuyHoldSPY()
    bars = pd.DataFrame(
        {"SPY": [float("nan"), 100.0, 101.0]},
        index=pd.to_datetime(["2026-01-02", "2026-01-03", "2026-01-04"]),
    )
    weights = s.generate_signals(bars, params={}, ctx=StrategyContext())
    assert weights["SPY"].iloc[0] == 0.0
    assert (weights["SPY"].iloc[1:] == 1.0).all()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_strategy_buyhold.py -v
```
Expected: FAIL.

- [ ] **Step 3: Implement `buy_hold_spy.py`**

Create `backend/app/quant/strategies/buy_hold_spy.py`:

```python
"""Buy & Hold SPY — benchmark for every other strategy."""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)


class BuyHoldSPY(Strategy):
    spec = StrategySpec(
        slug="buy-hold-spy",
        name="Buy & Hold SPY",
        category="benchmark",
        universe_kind="spy",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Always long the SPDR S&P 500 ETF (SPY) at 100% weight. "
            "Serves as the passive benchmark every active strategy is "
            "compared against."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {}

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        # Weight = 1 on every day SPY has a non-NaN price; 0 before that.
        spy = bars["SPY"]
        w = (spy.notna()).astype(float)
        return pd.DataFrame({"SPY": w}, index=bars.index)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_strategy_buyhold.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/quant/strategies/buy_hold_spy.py backend/tests/test_quant_strategy_buyhold.py
git commit -m "feat(quant): buy-hold-spy benchmark strategy"
```

---

## Task 12: Strategy — `sma-crossover`

**Files:**
- Create: `backend/app/quant/strategies/sma_crossover.py`
- Test: `backend/tests/test_quant_strategy_sma.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_strategy_sma.py`:

```python
import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.sma_crossover import SmaCrossover


def test_metadata():
    s = SmaCrossover()
    assert s.spec.slug == "sma-crossover"
    assert s.spec.category == "classic"
    assert s.spec.universe_kind == "spy"
    # Grid has fast / slow with fast < slow constraint applied at sweep time.
    assert set(s.sweep_grid.keys()) == {"fast", "slow"}


def test_generate_signals_long_when_fast_above_slow():
    s = SmaCrossover()
    # Construct a series that rises then falls: fast SMA crosses above slow then below.
    idx = pd.date_range("2026-01-01", periods=60, freq="B")
    prices = pd.Series(
        # Linearly rising 30 days, then linearly falling 30 days.
        list(range(100, 130)) + list(range(130, 100, -1)),
        index=idx,
    )
    bars = pd.DataFrame({"SPY": prices.astype(float)})
    weights = s.generate_signals(bars, params={"fast": 5, "slow": 20}, ctx=StrategyContext())
    # On the rising leg, the fast SMA should eventually exceed the slow SMA,
    # producing weight=1; on the falling leg, weight returns to 0.
    rising_late = weights["SPY"].iloc[24]   # late in the rising leg
    falling_late = weights["SPY"].iloc[55]
    assert rising_late == 1.0
    assert falling_late == 0.0


def test_generate_signals_zero_before_slow_window_filled():
    s = SmaCrossover()
    idx = pd.date_range("2026-01-01", periods=30, freq="B")
    prices = pd.Series(range(100, 130), index=idx).astype(float)
    bars = pd.DataFrame({"SPY": prices})
    weights = s.generate_signals(bars, params={"fast": 5, "slow": 20}, ctx=StrategyContext())
    # First (slow-1) rows must be 0 because the slow SMA is undefined.
    assert (weights["SPY"].iloc[:19] == 0.0).all()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_strategy_sma.py -v
```
Expected: FAIL.

- [ ] **Step 3: Implement `sma_crossover.py`**

Create `backend/app/quant/strategies/sma_crossover.py`:

```python
"""SMA crossover — long when fast-SMA > slow-SMA, flat otherwise.

Trades a single symbol (SPY). The classic trend-following baseline.
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)


class SmaCrossover(Strategy):
    spec = StrategySpec(
        slug="sma-crossover",
        name="SMA Crossover",
        category="classic",
        universe_kind="spy",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Long the SPDR S&P 500 ETF (SPY) when the fast simple moving "
            "average crosses above the slow simple moving average; flat "
            "otherwise. A canonical trend-following baseline strategy."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "fast": [10, 20, 50],
        "slow": [50, 100, 200],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        fast = int(params["fast"])
        slow = int(params["slow"])
        spy = bars["SPY"]
        fast_sma = spy.rolling(fast, min_periods=fast).mean()
        slow_sma = spy.rolling(slow, min_periods=slow).mean()
        long = (fast_sma > slow_sma).astype(float)
        long = long.fillna(0.0)
        return pd.DataFrame({"SPY": long}, index=bars.index)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_strategy_sma.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/quant/strategies/sma_crossover.py backend/tests/test_quant_strategy_sma.py
git commit -m "feat(quant): sma-crossover strategy (SPY single-name trend baseline)"
```

---

## Task 13: Registry

**Files:**
- Create: `backend/app/quant/registry.py`
- Test: `backend/tests/test_quant_registry.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_registry.py`:

```python
import pytest

from app.quant.registry import STRATEGIES, get_strategy, list_strategy_slugs


def test_strategies_contains_q1a_set():
    slugs = {s.spec.slug for s in STRATEGIES}
    assert {"buy-hold-spy", "sma-crossover"}.issubset(slugs)


def test_get_strategy_returns_instance():
    s = get_strategy("buy-hold-spy")
    assert s.spec.slug == "buy-hold-spy"


def test_get_strategy_unknown_raises():
    with pytest.raises(KeyError):
        get_strategy("not-a-strategy")


def test_list_strategy_slugs_is_sorted_with_benchmark_last():
    slugs = list_strategy_slugs()
    assert "buy-hold-spy" in slugs
    assert "sma-crossover" in slugs
    # Benchmark goes last for display ordering.
    assert slugs.index("buy-hold-spy") > slugs.index("sma-crossover")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_registry.py -v
```
Expected: FAIL.

- [ ] **Step 3: Implement `registry.py`**

Create `backend/app/quant/registry.py`:

```python
"""Strategy registry — one place that knows about every strategy.

Q1a ships with 2 entries. Q1b will append the remaining 7.
"""

from __future__ import annotations

from app.quant.strategies.base import Strategy
from app.quant.strategies.buy_hold_spy import BuyHoldSPY
from app.quant.strategies.sma_crossover import SmaCrossover

STRATEGIES: tuple[Strategy, ...] = (
    SmaCrossover(),
    BuyHoldSPY(),
)


def get_strategy(slug: str) -> Strategy:
    for s in STRATEGIES:
        if s.spec.slug == slug:
            return s
    raise KeyError(f"Unknown strategy slug: {slug}")


def list_strategy_slugs() -> list[str]:
    """Display order: classics + alpha alphabetically, benchmark last."""
    classics = sorted(
        s.spec.slug for s in STRATEGIES
        if s.spec.category in ("classic", "alpha")
    )
    benchmarks = sorted(
        s.spec.slug for s in STRATEGIES if s.spec.category == "benchmark"
    )
    return classics + benchmarks
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_registry.py -v
```
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/quant/registry.py backend/tests/test_quant_registry.py
git commit -m "feat(quant): strategy registry with 2 Q1a entries"
```

---

## Task 14: Engine — `run_single`

**Files:**
- Create: `backend/app/quant/engine.py`
- Test: `backend/tests/test_quant_engine.py`

The engine runs a strategy's weights through vectorbt + the cost model and returns equity, trades, and metrics. We start with the single-parameter path (`run_single`); the grid path (`run_grid`) lands in Task 15.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_engine.py`:

```python
import numpy as np
import pandas as pd

from app.quant.cost_model import CostModel
from app.quant.engine import EngineResult, run_single
from app.quant.strategies.base import StrategyContext
from app.quant.strategies.buy_hold_spy import BuyHoldSPY


def _spy_series(n: int = 100, start_price: float = 100.0, drift: float = 0.001):
    """Deterministic synthetic SPY price series — geometric drift, no noise."""
    idx = pd.date_range("2026-01-02", periods=n, freq="B")
    prices = start_price * (1 + drift) ** np.arange(n)
    return pd.DataFrame({"SPY": prices.astype(float)}, index=idx)


def test_run_single_buy_hold_grows_with_drift():
    bars = _spy_series(n=100, drift=0.001)
    res: EngineResult = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    # Buy & hold with zero costs ≈ SPY total return
    expected_growth = bars["SPY"].iloc[-1] / bars["SPY"].iloc[0]
    actual_growth = res.equity.iloc[-1] / 100_000
    assert abs(actual_growth - expected_growth) / expected_growth < 0.01


def test_run_single_returns_equity_indexed_by_date():
    bars = _spy_series(n=50)
    res = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    assert isinstance(res.equity, pd.Series)
    assert isinstance(res.equity.index, pd.DatetimeIndex)
    assert len(res.equity) == 50


def test_run_single_records_trades():
    bars = _spy_series(n=50)
    res = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    # Buy & hold should record at least 1 entry trade.
    assert len(res.trades) >= 1
    assert res.trades.iloc[0]["side"] in ("buy",)


def test_run_single_metrics_include_sharpe_and_max_drawdown():
    bars = _spy_series(n=252, drift=0.0008)
    res = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    assert "sharpe" in res.metrics
    assert "max_drawdown" in res.metrics
    assert "total_return" in res.metrics
    assert res.metrics["total_return"] > 0


def test_run_single_applies_slippage():
    bars = _spy_series(n=50)
    res_zero = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    res_slip = run_single(
        BuyHoldSPY(), bars, params={},
        cost_model=CostModel(commission=0, slippage_bps=50),  # 50 bps
        initial_equity=100_000,
    )
    # With slippage, final equity must be strictly less.
    assert res_slip.equity.iloc[-1] < res_zero.equity.iloc[-1]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_engine.py -v
```
Expected: FAIL — `app.quant.engine` doesn't exist.

- [ ] **Step 3: Implement engine.py (single-param path only)**

Create `backend/app/quant/engine.py`:

```python
"""Backtest engine — vectorbt wrappers + custom forward-step simulator.

This module is the boundary between the strategy framework (clean DataFrames
of target weights) and the execution machinery (orders + fills + equity +
metrics).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import vectorbt as vbt

from app.quant.cost_model import CostModel
from app.quant.strategies.base import Strategy, StrategyContext


@dataclass
class EngineResult:
    equity: pd.Series                      # indexed by date
    trades: pd.DataFrame                   # cols: date, symbol, side, qty, price, commission, notional
    metrics: dict[str, float]              # sharpe, max_drawdown, total_return, cagr, ...


def _portfolio_from_weights(
    weights: pd.DataFrame,
    close: pd.DataFrame,
    cost_model: CostModel,
    initial_equity: float,
) -> vbt.Portfolio:
    """Build a vbt.Portfolio from continuous target weights."""
    # vectorbt expects fees/slippage as fractions per side.
    fees = 0.0
    if cost_model.commission and initial_equity:
        fees = cost_model.commission / initial_equity   # crude per-fill fee → fraction
    slippage = cost_model.slippage_bps / 10_000.0

    # Align — drop dates where every column is NaN.
    weights = weights.reindex(close.index).fillna(0.0)
    # vectorbt's `from_orders` with size_type='targetpercent' rebalances to target weights.
    return vbt.Portfolio.from_orders(
        close=close,
        size=weights,
        size_type="targetpercent",
        init_cash=initial_equity,
        fees=fees,
        slippage=slippage,
        freq="D",
    )


def _extract_metrics(pf: vbt.Portfolio) -> dict[str, float]:
    stats = pf.stats(silence_warnings=True)
    # vectorbt stats names vary slightly across versions; pull defensively.
    def f(name: str, default: float = float("nan")) -> float:
        try:
            v = stats[name]
            return float(v) if v is not None else default
        except (KeyError, TypeError, ValueError):
            return default

    return {
        "total_return": f("Total Return [%]", default=0.0) / 100.0,
        "cagr": f("Annualized Return [%]", default=0.0) / 100.0,
        "sharpe": f("Sharpe Ratio", default=0.0),
        "sortino": f("Sortino Ratio", default=0.0),
        "calmar": f("Calmar Ratio", default=0.0),
        "max_drawdown": f("Max Drawdown [%]", default=0.0) / 100.0,
        "win_rate": f("Win Rate [%]", default=0.0) / 100.0,
        "volatility": f("Annualized Volatility [%]", default=0.0) / 100.0,
    }


def _extract_trades(pf: vbt.Portfolio) -> pd.DataFrame:
    """Convert vbt's trade records to our schema."""
    try:
        records = pf.orders.records_readable
    except Exception:
        return pd.DataFrame(columns=[
            "date", "symbol", "side", "qty", "price", "commission", "notional",
        ])
    if records is None or len(records) == 0:
        return pd.DataFrame(columns=[
            "date", "symbol", "side", "qty", "price", "commission", "notional",
        ])
    # records_readable columns vary by vbt version — expect at minimum:
    # 'Timestamp', 'Column', 'Size', 'Price', 'Fees', 'Side'
    out = pd.DataFrame({
        "date":       pd.to_datetime(records["Timestamp"]).dt.strftime("%Y-%m-%d"),
        "symbol":     records["Column"].astype(str),
        "side":       records["Side"].astype(str).str.lower().map({
                          "buy": "buy", "sell": "sell",
                      }).fillna("buy"),
        "qty":        records["Size"].astype(float).abs().astype(int),
        "price":      records["Price"].astype(float),
        "commission": records["Fees"].astype(float),
    })
    out["notional"] = out["qty"] * out["price"]
    return out


def run_single(
    strategy: Strategy,
    bars: pd.DataFrame,
    *,
    params: dict,
    cost_model: CostModel | None = None,
    initial_equity: float = 100_000.0,
    ctx: StrategyContext | None = None,
) -> EngineResult:
    """Run a single parameter setting through the engine."""
    cost_model = cost_model or CostModel()
    ctx = ctx or StrategyContext()
    weights = strategy.generate_signals(bars, params, ctx)
    pf = _portfolio_from_weights(weights, bars, cost_model, initial_equity)
    equity = pf.value()
    if isinstance(equity, pd.DataFrame):
        # Single-asset case — collapse to Series.
        if equity.shape[1] == 1:
            equity = equity.iloc[:, 0]
        else:
            equity = equity.sum(axis=1)
    return EngineResult(
        equity=equity,
        trades=_extract_trades(pf),
        metrics=_extract_metrics(pf),
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_engine.py -v
```
Expected: PASS (5 tests). Some vectorbt versions may print deprecation warnings — those are non-fatal.

- [ ] **Step 5: Commit**

```bash
git add backend/app/quant/engine.py backend/tests/test_quant_engine.py
git commit -m "feat(quant): engine.run_single — vectorbt wrapper with cost model + metrics"
```

---

## Task 15: Engine — `run_grid`

**Files:**
- Modify: `backend/app/quant/engine.py`
- Test: `backend/tests/test_quant_engine.py`

Grid path: take a `ParamGrid` (`{name: [values]}`), compute every valid combination, run each through `run_single`, return a DataFrame indexed by parameter tuple with metric columns. The SMA grid has a `fast < slow` constraint applied at the engine level.

- [ ] **Step 1: Extend the failing test**

Append to `backend/tests/test_quant_engine.py`:

```python
def test_run_grid_returns_one_row_per_valid_combo():
    from app.quant.engine import run_grid
    from app.quant.strategies.sma_crossover import SmaCrossover

    bars = _spy_series(n=300, drift=0.0008)
    sma = SmaCrossover()
    df = run_grid(
        sma, bars, grid=sma.sweep_grid,
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
        constraint=lambda p: p["fast"] < p["slow"],
    )
    # SMA grid: fast ∈ {10,20,50}, slow ∈ {50,100,200}; with fast<slow constraint:
    # exclude (50,50) → 8 valid combos.
    assert len(df) == 8
    assert {"fast", "slow"}.issubset(df.columns)
    assert "sharpe" in df.columns
    assert "total_return" in df.columns


def test_run_grid_without_constraint_runs_all_combos():
    from app.quant.engine import run_grid
    grid = {"a": [1, 2], "b": [10, 20, 30]}
    # Use BuyHoldSPY but pass an ignored grid — it doesn't read params.
    bars = _spy_series(n=50)
    df = run_grid(
        BuyHoldSPY(), bars, grid=grid,
        cost_model=CostModel(commission=0, slippage_bps=0),
        initial_equity=100_000,
    )
    assert len(df) == 6  # 2 × 3
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_engine.py -v
```
Expected: FAIL — `run_grid` not defined.

- [ ] **Step 3: Add `run_grid` to engine.py**

Append to `backend/app/quant/engine.py`:

```python
import itertools
from typing import Callable


def run_grid(
    strategy: Strategy,
    bars: pd.DataFrame,
    *,
    grid: dict[str, list],
    cost_model: CostModel | None = None,
    initial_equity: float = 100_000.0,
    ctx: StrategyContext | None = None,
    constraint: Callable[[dict], bool] | None = None,
) -> pd.DataFrame:
    """Run every parameter combination from `grid` through `run_single`.

    Returns a DataFrame with one row per valid combo. Columns:
        <param names from grid>, sharpe, total_return, cagr, sortino,
        calmar, max_drawdown, win_rate, volatility
    Rows are NOT sorted; caller picks the winner.
    """
    if not grid:
        # Single-row result with empty params.
        res = run_single(
            strategy, bars,
            params={}, cost_model=cost_model,
            initial_equity=initial_equity, ctx=ctx,
        )
        return pd.DataFrame([{**res.metrics}])

    names = list(grid.keys())
    rows: list[dict] = []
    for combo in itertools.product(*(grid[n] for n in names)):
        params = dict(zip(names, combo))
        if constraint and not constraint(params):
            continue
        res = run_single(
            strategy, bars,
            params=params, cost_model=cost_model,
            initial_equity=initial_equity, ctx=ctx,
        )
        rows.append({**params, **res.metrics})
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_engine.py -v
```
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/quant/engine.py backend/tests/test_quant_engine.py
git commit -m "feat(quant): engine.run_grid — parameter sweep over a ParamGrid with optional constraint"
```

---

## Task 16: Engine — `simulate_fills` primitive

**Files:**
- Modify: `backend/app/quant/engine.py`
- Test: `backend/tests/test_quant_engine.py`

`simulate_fills` is the **forward-step primitive**: given the strategy's current positions, target positions, and today's close prices, produce the list of buy/sell/short/cover trades and the resulting position dict — applying the same cost model as the backtest path. The Q1c forward-step loop will call this; Q1a only adds + tests the function.

- [ ] **Step 1: Extend the failing test**

Append to `backend/tests/test_quant_engine.py`:

```python
def test_simulate_fills_buys_when_target_higher():
    from app.quant.engine import simulate_fills
    current = {"SPY": {"qty": 0, "avg_cost": 0.0}}
    target = {"SPY": {"qty": 100, "weight": 1.0}}
    fills, new_positions = simulate_fills(
        current_positions=current, target_positions=target,
        prices={"SPY": 470.0}, cost_model=CostModel(commission=0, slippage_bps=5),
    )
    assert len(fills) == 1
    assert fills[0]["symbol"] == "SPY"
    assert fills[0]["side"] == "buy"
    assert fills[0]["qty"] == 100
    # 5 bps adverse: 470 * 1.0005 = 470.235
    assert abs(fills[0]["price"] - 470.235) < 1e-6
    assert new_positions["SPY"]["qty"] == 100


def test_simulate_fills_sells_when_target_lower():
    from app.quant.engine import simulate_fills
    current = {"SPY": {"qty": 100, "avg_cost": 470.0}}
    target = {"SPY": {"qty": 50, "weight": 0.5}}
    fills, new_positions = simulate_fills(
        current_positions=current, target_positions=target,
        prices={"SPY": 472.0}, cost_model=CostModel(commission=0, slippage_bps=5),
    )
    assert len(fills) == 1
    assert fills[0]["side"] == "sell"
    assert fills[0]["qty"] == 50
    assert new_positions["SPY"]["qty"] == 50


def test_simulate_fills_noop_when_target_equals_current():
    from app.quant.engine import simulate_fills
    current = {"SPY": {"qty": 100, "avg_cost": 470.0}}
    target = {"SPY": {"qty": 100, "weight": 1.0}}
    fills, new_positions = simulate_fills(
        current_positions=current, target_positions=target,
        prices={"SPY": 472.0}, cost_model=CostModel(),
    )
    assert fills == []
    assert new_positions["SPY"]["qty"] == 100


def test_simulate_fills_handles_new_and_closed_symbols():
    from app.quant.engine import simulate_fills
    current = {"AAPL": {"qty": 50, "avg_cost": 200.0}}
    target = {"MSFT": {"qty": 40, "weight": 1.0}}
    fills, new_positions = simulate_fills(
        current_positions=current, target_positions=target,
        prices={"AAPL": 210.0, "MSFT": 410.0},
        cost_model=CostModel(commission=0, slippage_bps=0),
    )
    sides = {(f["symbol"], f["side"]) for f in fills}
    assert ("AAPL", "sell") in sides
    assert ("MSFT", "buy") in sides
    assert "AAPL" not in new_positions
    assert new_positions["MSFT"]["qty"] == 40
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_engine.py -v
```
Expected: FAIL — `simulate_fills` not defined.

- [ ] **Step 3: Add `simulate_fills`**

Append to `backend/app/quant/engine.py`:

```python
from app.quant.cost_model import apply_slippage


def simulate_fills(
    *,
    current_positions: dict[str, dict],
    target_positions: dict[str, dict],
    prices: dict[str, float],
    cost_model: CostModel,
) -> tuple[list[dict], dict[str, dict]]:
    """Compute the fills required to move from current → target positions
    and return (fills, new_positions).

    `current_positions` / `target_positions`:
        symbol -> {qty: int, avg_cost: float[, weight: float]}
    `prices`: symbol -> close price for the day.

    `fills` is a list of dicts ready for `strategy_trades` insert.
    `new_positions` mirrors `current_positions` after applying the fills.
    """
    fills: list[dict] = []
    new: dict[str, dict] = {sym: dict(pos) for sym, pos in current_positions.items()}

    symbols = set(current_positions) | set(target_positions)
    for sym in sorted(symbols):
        cur_qty = current_positions.get(sym, {}).get("qty", 0)
        tgt_qty = target_positions.get(sym, {}).get("qty", 0)
        delta = tgt_qty - cur_qty
        if delta == 0:
            continue
        price_raw = prices.get(sym)
        if price_raw is None:
            # No price today — skip; the runner decides whether to liquidate.
            continue
        # Side mapping: positive delta when going from short to less-short is a "cover",
        # else "buy". Negative delta when going from long to less-long is "sell",
        # else "short". Q1a strategies are long-only so the simpler branch suffices.
        if delta > 0:
            side = "cover" if cur_qty < 0 else "buy"
        else:
            side = "short" if tgt_qty < 0 and cur_qty >= 0 else "sell"
        fill_price = apply_slippage(
            price_raw, side=side, slippage_bps=cost_model.slippage_bps,
        )
        qty = abs(delta)
        notional = qty * fill_price
        fills.append({
            "symbol": sym,
            "side": side,
            "qty": qty,
            "price": fill_price,
            "commission": cost_model.commission,
            "notional": notional,
        })
        # Update position
        if tgt_qty == 0:
            new.pop(sym, None)
        else:
            # Weighted-average cost basis on additive buys; reset on side flip.
            if cur_qty == 0 or (cur_qty > 0) != (tgt_qty > 0):
                new[sym] = {"qty": tgt_qty, "avg_cost": fill_price}
            elif (tgt_qty > cur_qty > 0) or (tgt_qty < cur_qty < 0):
                old_basis = current_positions[sym].get("avg_cost", fill_price)
                added = qty
                new_avg = (old_basis * abs(cur_qty) + fill_price * added) / abs(tgt_qty)
                new[sym] = {"qty": tgt_qty, "avg_cost": new_avg}
            else:
                # Partial close — keep existing avg_cost.
                new[sym] = {"qty": tgt_qty, "avg_cost": current_positions[sym]["avg_cost"]}
    return fills, new
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_engine.py -v
```
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/quant/engine.py backend/tests/test_quant_engine.py
git commit -m "feat(quant): engine.simulate_fills — forward-step primitive sharing the cost model"
```

---

## Task 17: Orchestration — `inception_walkforward` end-to-end

**Files:**
- Create: `backend/app/quant/orchestration.py`
- Test: `backend/tests/test_quant_orchestration.py`

This is the Q1a finale: a function that, given a Strategy and a bar warehouse, runs the full walk-forward backtest pipeline and persists everything — `StrategyRun` row, stitched equity (`EquityPoint`s with `phase="backtest"`), trades, and the parameter sweep. Q1c will wrap this in a background-job runner and HTTP endpoint; here we just make sure the orchestration is correct end-to-end.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_quant_orchestration.py`:

```python
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
    idx = pd.bdate_range("2018-01-02", periods=252 * years)
    prices = pd.Series(
        100.0 * (1.0008 ** range(len(idx))),
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
    # Override live_start_date so we have headroom for at least one window.
    strategy.spec.__dict__["inception_date"] = "2018-01-02"  # frozen dataclass workaround
    # Actually frozen — instead, mock by setting via construction. For Q1a the spec dates
    # already give enough headroom if seeded from 2015; but our seed starts in 2018.
    # We use the existing live_start_date=2025-01-02 from the spec.
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
            select(strategy_equity).where(strategy_equity.c.strategy_slug == "buy-hold-spy")
        ).all())
    # Same data + same params => same row count.
    assert n1 == n2 > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_quant_orchestration.py -v
```
Expected: FAIL — `app.quant.orchestration` doesn't exist.

- [ ] **Step 3: Implement `orchestration.py`**

Create `backend/app/quant/orchestration.py`:

```python
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
from app.quant.bars import load_close_matrix
from app.quant.cost_model import CostModel
from app.quant.engine import run_grid, run_single
from app.quant.strategies.base import Strategy, StrategyContext
from app.quant.universe import get_universe
from app.quant.walkforward import build_walkforward_windows, stitch_oos_equity

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            )

            if strategy.sweep_grid and not grid_df.empty:
                best_row = grid_df.sort_values("sharpe", ascending=False).iloc[0]
                best_params = {
                    k: best_row[k] for k in strategy.sweep_grid.keys()
                }
                # Cast numpy ints back to python ints for JSON.
                best_params = {k: int(v) if hasattr(v, "item") and float(v).is_integer()
                               else (float(v) if hasattr(v, "item") else v)
                               for k, v in best_params.items()}
                for _, row in grid_df.iterrows():
                    cell = {
                        "params": {k: int(row[k]) if hasattr(row[k], "item")
                                                    and float(row[k]).is_integer()
                                   else (float(row[k]) if hasattr(row[k], "item") else row[k])
                                   for k in strategy.sweep_grid.keys()},
                        "sharpe": float(row["sharpe"]),
                    }
                    sweep_acc.append(cell)
            else:
                best_params = {}

            oos = run_single(
                strategy, test_bars, params=best_params,
                cost_model=cost_model, initial_equity=initial_equity,
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && pytest tests/test_quant_orchestration.py -v
```
Expected: PASS (3 tests). Note: vectorbt may emit warnings — those are not failures.

- [ ] **Step 5: Run the full quant test suite to catch any regressions**

```bash
cd backend && pytest tests/test_quant_*.py -v
```
Expected: all quant tests PASS. Total count: ~40 tests across the 10 test files.

- [ ] **Step 6: Run the FULL backend test suite to catch any side effects on other domains**

```bash
cd backend && pytest -v
```
Expected: all previously-passing tests still pass + the new ~40 quant tests pass. Total green.

- [ ] **Step 7: Commit**

```bash
git add backend/app/quant/orchestration.py backend/tests/test_quant_orchestration.py
git commit -m "feat(quant): inception_walkforward orchestrator end-to-end

Wires bars → walk-forward windows → grid search per window → OOS
stitching → persisted equity/trades/run + chosen_params. Q1c will wrap
this in a background-job runner + HTTP endpoint."
```

---

## Task 18: Smoke test against real yfinance data (manual verification)

This task isn't TDD; it's a manual sanity check that the whole pipeline works against real market data before we move on to Q1b. Discoveries from this task may produce small follow-up commits.

- [ ] **Step 1: Fetch real SPY history**

From `backend/`:

```bash
python -c "
from app.database import init_db
from app.quant.bars import fetch_and_cache
init_db()
n = fetch_and_cache(['SPY'], start='2018-01-02', end='2025-01-02')
print(f'wrote {n} rows')
"
```
Expected: writes ~1,750 rows (7 years × 252 business days).

- [ ] **Step 2: Run inception walk-forward for `buy-hold-spy`**

```bash
python -c "
from app.database import init_db
from app.quant.orchestration import inception_walkforward
from app.quant.strategies.buy_hold_spy import BuyHoldSPY
init_db()
run_id = inception_walkforward(BuyHoldSPY())
print('run_id:', run_id)
"
```
Expected: completes in <30 s, prints a run_id, no traceback.

- [ ] **Step 3: Inspect the resulting equity curve**

```bash
python -c "
import json
from sqlalchemy import select
from app.database import get_engine, strategy_equity, strategy_runs
init = __import__('app.database', fromlist=['init_db']).init_db
init()
with get_engine().begin() as conn:
    rows = conn.execute(
        select(strategy_equity).where(
            strategy_equity.c.strategy_slug == 'buy-hold-spy'
        ).order_by(strategy_equity.c.date)
    ).all()
    run = conn.execute(
        select(strategy_runs).where(
            strategy_runs.c.strategy_slug == 'buy-hold-spy'
        ).order_by(strategy_runs.c.id.desc())
    ).first()
print('equity points:', len(rows))
print('first / last equity:', rows[0].equity, '→', rows[-1].equity)
print('summary:', json.loads(run.summary_metrics))
"
```
Expected: prints ~4 years of equity points (the OOS portion across 4 walk-forward test windows), first ≈ 100,000, last positive total return, sharpe and max_drawdown printed. Sanity: SPY 2021–2024 was up roughly 50–60% — total_return should be in that ballpark (before costs).

- [ ] **Step 4: Run `sma-crossover` walk-forward**

```bash
python -c "
from app.database import init_db
from app.quant.orchestration import inception_walkforward
from app.quant.strategies.sma_crossover import SmaCrossover
init_db()
run_id = inception_walkforward(SmaCrossover())
print('run_id:', run_id)
"
```
Expected: completes in <2 min (8 param combos × 4 windows = 32 vectorbt runs). Prints run_id, no traceback.

- [ ] **Step 5: Confirm chosen_params is set**

```bash
python -c "
import json
from sqlalchemy import select
from app.database import get_engine, strategies
init = __import__('app.database', fromlist=['init_db']).init_db
init()
with get_engine().begin() as conn:
    row = conn.execute(
        select(strategies).where(strategies.c.slug == 'sma-crossover')
    ).first()
print('chosen_params:', json.loads(row.chosen_params))
"
```
Expected: prints something like `{'fast': 50, 'slow': 200}` (or another valid fast<slow combo) — confirms the grid search picked a winner.

- [ ] **Step 6: Commit any small fixes discovered, then push**

If steps 1–5 surfaced any bugs (e.g., vectorbt API surprises specific to your installed version), fix them as small dedicated commits referencing the surprise. Otherwise just push:

```bash
git push origin main
```

---

## Self-review

**Spec coverage** (mapping plan tasks → spec sections):
- Spec §4.1 directory layout → Tasks 6–17 create the matching files.
- Spec §4.2 inception walk-forward pipeline → Task 17.
- Spec §4.2 forward-step path → Task 16 (`simulate_fills` primitive only; full runner is Q1c).
- Spec §4.3 vectorbt `run_grid`/`run_single`/`simulate_fills` → Tasks 14–16.
- Spec §4.4 cost model (commission=$0, slippage=5bps, $100k starting, equal-weight) → Task 8 + applied throughout 14–17.
- Spec §5.1 strategies — only #1 `sma-crossover` and #6 `buy-hold-spy` land in Q1a (Tasks 11–12); the other 7 are explicitly Q1b.
- Spec §6 data model → Tasks 2–4 (DB tables) + Task 5 (Pydantic models).
- Spec §9 error handling → orchestrator wraps run in try/except writing `status="failed"` with `error` (Task 17); missing-bars / yfinance-failure cases are exercised in Q1c when the scheduler/runner lands.
- Spec §10 testing → TDD throughout, plus Task 18 manual smoke against real yfinance data.
- Spec §11 performance budget → `sma-crossover` walk-forward (8 combos × ~4 windows × ~5 yrs) targets <2 min per Task 18 step 4 (extrapolates well under the 10-min spec target for all 9 strategies).
- Spec §12 security → all DB writes go through the existing engine; no HTTP surface in Q1a, so no auth surface to test (lands in Q1c).
- Spec §13 plan decomposition → this is Q1a; Q1b/c/d each get their own plan.

**No unaddressed spec requirements remain in Q1a's scope.** Routes, scheduler jobs, the forward-step loop, frontend, and the other 7 strategies are explicitly deferred to Q1b/c/d — listed at the top under "Out of scope for Q1a".

**Placeholder scan:** the only "fill in" is the S&P 500 symbol list in Task 6 (universe.py). It's not a placeholder — it's a deliberate "paste in the static list" step with a clear normalization rule (BRK.B → BRK-B, BF.B → BF-B) and a verifiable acceptance criterion (≥480 symbols, test passes). The plan is explicit about this being a one-time copy-in.

**Type/name consistency check:**
- `EquityPoint` Pydantic model (Task 5) ↔ `strategy_equity` table columns (Task 4): both have `date, equity, cash, gross_exposure, net_exposure, daily_return, phase` — matches.
- `TradeRecord` Pydantic model (Task 5) ↔ `strategy_trades` columns (Task 4) ↔ `simulate_fills` output dict (Task 16): all use `date, symbol, side, qty, price, commission, notional, phase` — matches. `simulate_fills` omits `phase` from the per-fill dict; the orchestrator (Task 17) and the future forward-step runner (Q1c) inject `phase` at write time. Verified.
- `CostModel` dataclass (Task 8) used by `engine` (Tasks 14–16) and `orchestration` (Task 17) — single source of truth.
- `StrategyContext` (Task 10) appears in `run_single` / `run_grid` (Tasks 14–15) signatures — matches.
- `Strategy` ABC's `generate_signals` returns target weights; engine treats them as `targetpercent` via vectorbt — consistent.

No type drift found.
