# Quant Lab Q1b — Remaining 7 Strategies + Context Wiring

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the remaining 7 strategies the Quant Lab spec calls for — 4 more "classics" (RSI mean-reversion, cross-sectional momentum, pairs trading, Bollinger breakout) and 3 "alpha" strategies that read from the dashboard's existing data (news-sentiment momentum, macro-regime overlay, multi-factor combo). Extend the orchestrator + cost model so the strategies that need shorting and auxiliary context get them.

**Architecture:** Builds on Q1a. New strategy modules under `backend/app/quant/strategies/`. Three new "accessor" modules (`news_signal`, `econ_signal`, `fundamentals`) that read the dashboard's existing Postgres tables (`news_*`, `econ_series`) and yfinance fundamentals into the `StrategyContext`. Engine + orchestrator get the small extensions needed for shorting and context population. After Q1b: 9 strategies all backtestable end-to-end on real data.

**Tech Stack:** Same as Q1a — Python 3.11+, FastAPI app skeleton (only package additions here), SQLAlchemy Core, `vectorbt` 1.0.0, `quantstats`, `yfinance`, `statsmodels` (new — for cointegration in pairs trading), pandas, pytest.

**Spec:** `docs/superpowers/specs/2026-05-22-quant-lab-design.md` §5 (strategies #2–5 and #7–9).

**Out of scope for Q1b (do not implement):**
- HTTP routes (`/api/quant/*`) — Q1c
- APScheduler `warm_bars` / `forward_step_all_strategies` jobs — Q1c
- The continuous forward-step loop — Q1c
- Frontend — Q1d

---

## Background — Q1a state at the time of this plan

`main` is at the Q1a merge commit (`4b21ab6`). 233 backend tests passing. In place:
- `app.quant.universe.get_universe("spy"|"sp500"|"pairs-fixed"|"news-top100")` returns symbol tuples.
- `app.quant.bars.fetch_and_cache`, `load_bars`, `load_close_matrix` work against real yfinance.
- `app.quant.cost_model.CostModel(commission=0, slippage_bps=5, allow_short=False)` + `apply_slippage(price, side, slippage_bps)`.
- `app.quant.walkforward.build_walkforward_windows`, `stitch_oos_equity`.
- `app.quant.strategies.base.Strategy`, `StrategySpec`, `StrategyContext{news_clusters, econ_series, fundamentals}`, `ParamGrid`.
- `app.quant.strategies.buy_hold_spy.BuyHoldSPY`, `app.quant.strategies.sma_crossover.SmaCrossover`.
- `app.quant.registry.STRATEGIES`, `get_strategy`, `list_strategy_slugs`.
- `app.quant.engine.run_single`, `run_grid`, `simulate_fills`, `EngineResult`.
- `app.quant.orchestration.inception_walkforward(strategy, ...)` — handles single-name and multi-name (S&P 500) universes; persists everything to the 6 quant tables.

Existing tables used by Q1b alpha strategies (already created in earlier phases):
- `news_articles` (Phase 3): `id, cluster_id, title, summary, url, source, published_at, category, image_url`.
- `news_clusters` (Phase 3): `id, headline, summary, category, source_count, article_count, momentum, status, first_published_at, latest_published_at, centroid, rank_order`.
- `econ_series` (Phase 2): `series_id, date, value`.

Look in `backend/app/database.py` to see column types if needed. Do NOT modify those tables.

---

## File Map

**Modified:**
- `backend/requirements.txt` — add `statsmodels` (cointegration for pairs trading)
- `backend/app/quant/registry.py` — append 7 new strategy entries
- `backend/app/quant/orchestration.py` — extend `inception_walkforward` to populate `StrategyContext` from the new accessor modules
- `backend/app/quant/cost_model.py` — add a helper `target_qty_from_weight(weight, equity, price)` that handles negative weights (shorts) uniformly

**New strategy modules:**
- `backend/app/quant/strategies/rsi_mean_reversion.py`
- `backend/app/quant/strategies/cross_sectional_momentum.py`
- `backend/app/quant/strategies/pairs_trading.py`
- `backend/app/quant/strategies/bollinger_breakout.py`
- `backend/app/quant/strategies/news_sentiment_momentum.py`
- `backend/app/quant/strategies/macro_regime_overlay.py`
- `backend/app/quant/strategies/multi_factor_combo.py`

**New accessor modules:**
- `backend/app/quant/news_signal.py` — reads news_clusters + news_articles, produces per-symbol coverage + sentiment scores
- `backend/app/quant/econ_signal.py` — reads econ_series, exposes macro-regime classifier
- `backend/app/quant/fundamentals.py` — yfinance Ticker.info wrapper + file-backed cache

**New tests** (one file per new module):
- `backend/tests/test_quant_strategy_rsi.py`
- `backend/tests/test_quant_strategy_xs_momentum.py`
- `backend/tests/test_quant_strategy_pairs.py`
- `backend/tests/test_quant_strategy_bollinger.py`
- `backend/tests/test_quant_strategy_news_sentiment.py`
- `backend/tests/test_quant_strategy_macro_regime.py`
- `backend/tests/test_quant_strategy_multi_factor.py`
- `backend/tests/test_quant_news_signal.py`
- `backend/tests/test_quant_econ_signal.py`
- `backend/tests/test_quant_fundamentals.py`
- `backend/tests/test_quant_orchestration_alpha.py` — orchestrator wiring for alpha strategies

---

## Task 1: Add `statsmodels` dep + shorting helper in cost_model

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/quant/cost_model.py`
- Modify: `backend/tests/test_quant_cost_model.py`

- [ ] **Step 1: Add the dep**

In `backend/requirements.txt`, append:
```
statsmodels>=0.14
```

- [ ] **Step 2: Install it**

```bash
/Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/pip install -r backend/requirements.txt
/Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -c "from statsmodels.tsa.stattools import coint; print('ok')"
```
Expected: prints `ok`.

- [ ] **Step 3: Extend the failing test**

Append to `backend/tests/test_quant_cost_model.py`:

```python
def test_target_qty_from_weight_positive():
    from app.quant.cost_model import target_qty_from_weight
    # 1.0 weight * $100k / $200 = 500 shares
    assert target_qty_from_weight(weight=1.0, equity=100_000, price=200.0) == 500


def test_target_qty_from_weight_negative_is_short():
    from app.quant.cost_model import target_qty_from_weight
    # -0.5 weight * $100k / $200 = -250 shares (short)
    assert target_qty_from_weight(weight=-0.5, equity=100_000, price=200.0) == -250


def test_target_qty_from_weight_zero_price_returns_zero():
    from app.quant.cost_model import target_qty_from_weight
    assert target_qty_from_weight(weight=0.5, equity=100_000, price=0.0) == 0


def test_target_qty_from_weight_floors_to_int():
    from app.quant.cost_model import target_qty_from_weight
    # 0.33 weight * 100k / 199.5 = 165.4... → 165
    assert target_qty_from_weight(weight=0.33, equity=100_000, price=199.5) == 165
```

Run `cd backend && /Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -m pytest tests/test_quant_cost_model.py -v` — expect FAIL on the 4 new tests.

- [ ] **Step 4: Implement**

Append to `backend/app/quant/cost_model.py`:

```python
def target_qty_from_weight(*, weight: float, equity: float, price: float) -> int:
    """Convert a target portfolio weight into an integer share quantity.

    Negative weights produce negative quantities (short positions).
    Zero or invalid price returns 0 to avoid division errors.
    """
    if price <= 0 or equity <= 0:
        return 0
    raw = (weight * equity) / price
    # floor toward zero for both sides (i.e., truncate; do NOT round to nearest)
    return int(raw) if raw >= 0 else -int(-raw)
```

- [ ] **Step 5: Run tests + commit**

```bash
cd backend && /Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -m pytest tests/test_quant_cost_model.py -v
```
Expect 11 passing.

```bash
cd backend && /Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -m pytest --tb=no -q
```
Expect 237 passing.

```bash
git add backend/requirements.txt backend/app/quant/cost_model.py backend/tests/test_quant_cost_model.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): add statsmodels dep + target_qty_from_weight helper

statsmodels is needed for pairs-trading cointegration. The qty helper
gives every strategy a uniform way to translate target weights into
integer share quantities, including shorts.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Bollinger breakout strategy

**Files:**
- Create: `backend/app/quant/strategies/bollinger_breakout.py`
- Create: `backend/tests/test_quant_strategy_bollinger.py`

Follows the `BuyHoldSPY` / `SmaCrossover` pattern. SPY single-name, sweep grid `lookback ∈ {10, 20, 30}`, `std ∈ {1.5, 2, 2.5}` (9 combos).

- [ ] **Step 1: Write the failing test**

```python
import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.bollinger_breakout import BollingerBreakout


def test_metadata():
    s = BollingerBreakout()
    assert s.spec.slug == "bollinger-breakout"
    assert s.spec.category == "classic"
    assert s.spec.universe_kind == "spy"
    assert set(s.sweep_grid.keys()) == {"lookback", "std"}


def test_generate_signals_long_on_upper_band_breakout():
    s = BollingerBreakout()
    # Build a series with a clear breakout above 2-sigma upper band.
    base = [100.0] * 30 + [102.0] * 10 + [110.0] * 20   # quiet → calm → jump up
    idx = pd.date_range("2026-01-01", periods=len(base), freq="B")
    bars = pd.DataFrame({"SPY": base}, index=idx)
    w = s.generate_signals(bars, params={"lookback": 20, "std": 2.0}, ctx=StrategyContext())
    # On a sustained move above the upper band, late in the breakout, should be long.
    assert w["SPY"].iloc[-1] == 1.0


def test_generate_signals_flat_below_middle_band():
    s = BollingerBreakout()
    # Pure noise around 100 — no breakout.
    base = [100.0 + (0.5 if i % 2 else -0.5) for i in range(60)]
    idx = pd.date_range("2026-01-01", periods=len(base), freq="B")
    bars = pd.DataFrame({"SPY": base}, index=idx)
    w = s.generate_signals(bars, params={"lookback": 20, "std": 2.0}, ctx=StrategyContext())
    # No breakout → stays flat.
    assert (w["SPY"].iloc[20:] == 0.0).all()


def test_generate_signals_zero_before_lookback_filled():
    s = BollingerBreakout()
    idx = pd.date_range("2026-01-01", periods=30, freq="B")
    bars = pd.DataFrame({"SPY": [100.0] * 30}, index=idx)
    w = s.generate_signals(bars, params={"lookback": 20, "std": 2.0}, ctx=StrategyContext())
    assert (w["SPY"].iloc[:19] == 0.0).all()
```

Run test — expect FAIL.

- [ ] **Step 2: Implement**

```python
"""Bollinger breakout — long when close > upper band, exit on cross-below middle band.

Trades a single symbol (SPY). Volatility-breakout classic.
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)


class BollingerBreakout(Strategy):
    spec = StrategySpec(
        slug="bollinger-breakout",
        name="Bollinger Breakout",
        category="classic",
        universe_kind="spy",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Go long the SPDR S&P 500 ETF (SPY) on a close above the upper "
            "Bollinger band; exit when the close drops back below the "
            "middle (moving-average) band. Captures momentum breakouts "
            "out of low-volatility regimes."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "lookback": [10, 20, 30],
        "std": [1.5, 2.0, 2.5],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        lookback = int(params["lookback"])
        std_mult = float(params["std"])
        spy = bars["SPY"]
        mid = spy.rolling(lookback, min_periods=lookback).mean()
        sd = spy.rolling(lookback, min_periods=lookback).std()
        upper = mid + std_mult * sd

        # Stateful entry/exit: long once close > upper, hold until close < mid.
        long = pd.Series(0.0, index=spy.index)
        holding = False
        for i in range(len(spy)):
            if pd.isna(upper.iloc[i]) or pd.isna(mid.iloc[i]):
                continue
            if not holding and spy.iloc[i] > upper.iloc[i]:
                holding = True
            elif holding and spy.iloc[i] < mid.iloc[i]:
                holding = False
            long.iloc[i] = 1.0 if holding else 0.0
        return pd.DataFrame({"SPY": long}, index=bars.index)
```

- [ ] **Step 3: Add to registry**

Edit `backend/app/quant/registry.py`. Add the import and the instance to `STRATEGIES`:

```python
from app.quant.strategies.bollinger_breakout import BollingerBreakout
```

```python
STRATEGIES: tuple[Strategy, ...] = (
    SmaCrossover(),
    BollingerBreakout(),       # ← new
    BuyHoldSPY(),
)
```

- [ ] **Step 4: Run tests + commit**

```bash
cd backend && /Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -m pytest tests/test_quant_strategy_bollinger.py tests/test_quant_registry.py -v
```
Expect: bollinger 4 PASS, registry 4 PASS.

```bash
cd backend && /Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -m pytest --tb=no -q
```
Expect 241 passing.

```bash
git add backend/app/quant/strategies/bollinger_breakout.py backend/app/quant/registry.py backend/tests/test_quant_strategy_bollinger.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): bollinger-breakout strategy (SPY volatility breakout)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: RSI mean-reversion strategy

**Files:**
- Create: `backend/app/quant/strategies/rsi_mean_reversion.py`
- Create: `backend/tests/test_quant_strategy_rsi.py`
- Modify: `backend/app/quant/registry.py`

S&P 500 universe, per-name; max 20 concurrent positions selected by lowest RSI when more than 20 signals are present. Sweep grid: `lookback ∈ {7, 14, 21}`, `lower ∈ {20, 25, 30}`, `upper ∈ {55, 65, 75}`.

- [ ] **Step 1: Write the failing test**

```python
import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.rsi_mean_reversion import RsiMeanReversion


def test_metadata():
    s = RsiMeanReversion()
    assert s.spec.slug == "rsi-mean-reversion"
    assert s.spec.category == "classic"
    assert s.spec.universe_kind == "sp500"
    assert set(s.sweep_grid.keys()) == {"lookback", "lower", "upper"}


def test_signals_long_when_rsi_below_lower():
    s = RsiMeanReversion()
    # Build a name with a sharp drawdown so RSI dips below 30.
    idx = pd.date_range("2026-01-01", periods=40, freq="B")
    # First 20 days drift up, last 20 days monotonic down → RSI collapses.
    prices = list(range(100, 120)) + list(range(120, 100, -1))
    bars = pd.DataFrame({"AAA": [float(p) for p in prices]}, index=idx)
    w = s.generate_signals(bars, params={"lookback": 14, "lower": 30, "upper": 70},
                           ctx=StrategyContext())
    # Late in the downtrend, RSI < 30 → long signal.
    assert w["AAA"].iloc[-1] > 0


def test_signals_max_20_concurrent_positions():
    s = RsiMeanReversion()
    # 30 names, all in deep oversold state on day 30 → only 20 should be selected.
    idx = pd.date_range("2026-01-01", periods=30, freq="B")
    data = {}
    for i in range(30):
        # All names collapse identically from 120 → 90 over the window.
        data[f"S{i:02d}"] = [120.0 - j * 1.0 for j in range(30)]
    bars = pd.DataFrame(data, index=idx)
    w = s.generate_signals(bars, params={"lookback": 14, "lower": 30, "upper": 70},
                           ctx=StrategyContext())
    last_row = w.iloc[-1]
    n_active = int((last_row > 0).sum())
    assert n_active <= 20
```

Run — expect FAIL.

- [ ] **Step 2: Implement**

```python
"""RSI mean reversion — long when RSI < lower, exit when RSI > upper.

S&P 500 universe, per-name. Caps concurrent positions at 20 by selecting
the names with the lowest current RSI (most oversold). Equal-weight
across active positions.
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)

_MAX_CONCURRENT = 20


def _rsi(prices: pd.Series, lookback: int) -> pd.Series:
    """Wilder's RSI."""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / lookback, adjust=False, min_periods=lookback).mean()
    avg_loss = loss.ewm(alpha=1 / lookback, adjust=False, min_periods=lookback).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


class RsiMeanReversion(Strategy):
    spec = StrategySpec(
        slug="rsi-mean-reversion",
        name="RSI Mean Reversion",
        category="classic",
        universe_kind="sp500",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Go long an S&P 500 name when its Wilder RSI drops below the "
            "lower threshold (oversold), exit when RSI crosses back above "
            "the upper threshold. Caps the book at 20 concurrent positions "
            "by selecting the most-oversold names when more signals fire."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "lookback": [7, 14, 21],
        "lower": [20, 25, 30],
        "upper": [55, 65, 75],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        lookback = int(params["lookback"])
        lower = float(params["lower"])
        upper = float(params["upper"])

        rsi = bars.apply(lambda col: _rsi(col, lookback))

        # Stateful per-symbol entry/exit, then cap to 20 names by lowest RSI.
        holdings = pd.DataFrame(0.0, index=bars.index, columns=bars.columns)
        active: dict[str, bool] = {c: False for c in bars.columns}
        for t in range(len(bars.index)):
            row_rsi = rsi.iloc[t]
            # Update entry/exit state per name.
            for sym in bars.columns:
                r = row_rsi[sym]
                if pd.isna(r):
                    continue
                if not active[sym] and r < lower:
                    active[sym] = True
                elif active[sym] and r > upper:
                    active[sym] = False

            # Cap to 20 by lowest RSI.
            active_syms = [s for s, on in active.items() if on]
            if len(active_syms) > _MAX_CONCURRENT:
                ranked = row_rsi[active_syms].sort_values().index.tolist()
                active_syms = ranked[:_MAX_CONCURRENT]

            if active_syms:
                w = 1.0 / len(active_syms)
                for sym in active_syms:
                    holdings.iloc[t, holdings.columns.get_loc(sym)] = w
        return holdings
```

- [ ] **Step 3: Register**

Update `registry.py`:

```python
from app.quant.strategies.rsi_mean_reversion import RsiMeanReversion
```

Insert `RsiMeanReversion(),` into `STRATEGIES` after `SmaCrossover()`.

- [ ] **Step 4: Run tests + commit**

```bash
cd backend && /Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -m pytest tests/test_quant_strategy_rsi.py tests/test_quant_registry.py -v
```
Expect: rsi 3 PASS + registry 4 PASS.

Then full suite. Expected total: 244 passing.

```bash
git add backend/app/quant/strategies/rsi_mean_reversion.py backend/app/quant/registry.py backend/tests/test_quant_strategy_rsi.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): rsi-mean-reversion strategy (S&P 500 per-name, max 20 concurrent)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Cross-sectional momentum strategy

**Files:**
- Create: `backend/app/quant/strategies/cross_sectional_momentum.py`
- Create: `backend/tests/test_quant_strategy_xs_momentum.py`
- Modify: `backend/app/quant/registry.py`

S&P 500 universe. Monthly rebalance: each month, compute the "12-1" return (12-month return minus the most recent month — Jegadeesh-Titman style), rank, long top decile equal-weight. Sweep grid: `lookback ∈ {6, 9, 12} months`, `skip ∈ {0, 1} months`, `top_pct ∈ {5, 10, 20}` percent.

- [ ] **Step 1: Test**

```python
import numpy as np
import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.cross_sectional_momentum import CrossSectionalMomentum


def test_metadata():
    s = CrossSectionalMomentum()
    assert s.spec.slug == "cross-sectional-momentum"
    assert s.spec.category == "classic"
    assert s.spec.universe_kind == "sp500"
    assert set(s.sweep_grid.keys()) == {"lookback", "skip", "top_pct"}


def test_picks_top_decile_each_month():
    s = CrossSectionalMomentum()
    # 20 names, monotonic increasing momentum: S00 worst, S19 best.
    idx = pd.bdate_range("2024-01-02", periods=300)
    data = {}
    for i in range(20):
        # Each name drifts at i bps/day → 20 distinct return ranks.
        data[f"S{i:02d}"] = 100.0 * (1 + 0.0001 * i) ** np.arange(len(idx))
    bars = pd.DataFrame(data, index=idx)
    w = s.generate_signals(bars, params={"lookback": 9, "skip": 1, "top_pct": 10},
                           ctx=StrategyContext())
    # Late in the series, top 10% of 20 = top 2 names → S18, S19.
    last = w.iloc[-1]
    assert (last["S19"] > 0) and (last["S18"] > 0)
    # Lowest-momentum names should be flat.
    assert last["S00"] == 0


def test_zero_until_lookback_plus_skip_months_elapsed():
    s = CrossSectionalMomentum()
    idx = pd.bdate_range("2024-01-02", periods=120)   # ~6 months only
    data = {f"S{i:02d}": [100.0 + i] * len(idx) for i in range(10)}
    bars = pd.DataFrame(data, index=idx)
    w = s.generate_signals(bars, params={"lookback": 9, "skip": 1, "top_pct": 10},
                           ctx=StrategyContext())
    # Not enough history → all weights zero.
    assert (w.values == 0).all()
```

- [ ] **Step 2: Implement**

```python
"""Cross-sectional momentum — long top decile by 12-1 month return.

S&P 500. Monthly rebalance on the last business day. Sweep grid:
lookback (months), skip (months — typically 1 to drop the prior month
that often shows mean reversion), top_pct.
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)

_DAYS_PER_MONTH = 21


class CrossSectionalMomentum(Strategy):
    spec = StrategySpec(
        slug="cross-sectional-momentum",
        name="Cross-Sectional Momentum",
        category="classic",
        universe_kind="sp500",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Each month, rank S&P 500 names by their lookback-month total "
            "return excluding the most recent `skip` month(s), then go "
            "long the top decile equal-weight. The classic 12-1 momentum "
            "factor (Jegadeesh & Titman 1993)."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "lookback": [6, 9, 12],
        "skip": [0, 1],
        "top_pct": [5, 10, 20],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        lookback_m = int(params["lookback"])
        skip_m = int(params["skip"])
        top_pct = int(params["top_pct"])

        # Required history in trading days.
        lookback_d = lookback_m * _DAYS_PER_MONTH
        skip_d = skip_m * _DAYS_PER_MONTH
        warmup = lookback_d + skip_d

        # Compute the rolling momentum signal at each day, then forward-fill
        # over the month so weights only change on month-end (monthly rebalance).
        if len(bars) < warmup:
            return pd.DataFrame(0.0, index=bars.index, columns=bars.columns)

        # Momentum at day t = price[t-skip_d] / price[t-skip_d-lookback_d] - 1
        shifted = bars.shift(skip_d)
        base = bars.shift(skip_d + lookback_d)
        momentum = (shifted / base) - 1.0

        # Resample momentum to month-end for rebalance dates.
        month_ends = bars.resample("ME").last().index
        month_ends = month_ends[month_ends >= bars.index[warmup]]

        weights = pd.DataFrame(0.0, index=bars.index, columns=bars.columns)
        for me in month_ends:
            # Last available trading day <= month-end.
            idx_pos = bars.index.get_indexer([me], method="ffill")[0]
            if idx_pos < 0:
                continue
            mrow = momentum.iloc[idx_pos].dropna()
            if mrow.empty:
                continue
            n_pick = max(1, int(len(mrow) * top_pct / 100))
            winners = mrow.sort_values(ascending=False).head(n_pick).index
            w = 1.0 / len(winners)
            # Apply from this rebalance date forward until the next month-end.
            next_me_pos = bars.index.get_indexer(
                [bars.index[idx_pos + 1] if idx_pos + 1 < len(bars.index) else me]
            )[0]
            # Hold from idx_pos+1 (next day) until next rebalance.
            for sym in winners:
                col_idx = weights.columns.get_loc(sym)
                weights.iloc[idx_pos:, col_idx] = w
        # Re-zero rows after each rebalance hits the next rebalance.
        # Simpler: re-do via groupby month
        # The simpler correct approach: build a month-indexed weights df, forward-fill, then merge.
        # Override the above with a cleaner implementation:
        return _monthly_rebalance_weights(
            bars=bars, momentum=momentum, top_pct=top_pct, warmup=warmup
        )


def _monthly_rebalance_weights(
    *, bars: pd.DataFrame, momentum: pd.DataFrame, top_pct: int, warmup: int,
) -> pd.DataFrame:
    weights = pd.DataFrame(0.0, index=bars.index, columns=bars.columns)
    if len(bars) <= warmup:
        return weights
    # Use the LAST trading day of each calendar month as the rebalance day.
    month_periods = bars.index.to_period("M")
    last_day_per_month = pd.Series(bars.index, index=bars.index).groupby(month_periods).max()
    rebal_days = [d for d in last_day_per_month.values if d >= bars.index[warmup]]
    current_winners: list[str] = []
    rebal_set = set(rebal_days)
    for i, day in enumerate(bars.index):
        if day in rebal_set:
            mrow = momentum.loc[day].dropna()
            if not mrow.empty:
                n_pick = max(1, int(len(mrow) * top_pct / 100))
                current_winners = mrow.sort_values(ascending=False).head(n_pick).index.tolist()
        if current_winners:
            w = 1.0 / len(current_winners)
            for sym in current_winners:
                weights.iloc[i, weights.columns.get_loc(sym)] = w
    return weights
```

- [ ] **Step 3: Register + run tests + commit**

```python
from app.quant.strategies.cross_sectional_momentum import CrossSectionalMomentum
```

Insert `CrossSectionalMomentum(),` into `STRATEGIES`.

Tests pass. Full suite at 247.

```bash
git add backend/app/quant/strategies/cross_sectional_momentum.py backend/app/quant/registry.py backend/tests/test_quant_strategy_xs_momentum.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): cross-sectional-momentum (S&P 500, monthly top-decile rebalance)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Pairs trading strategy

**Files:**
- Create: `backend/app/quant/strategies/pairs_trading.py`
- Create: `backend/tests/test_quant_strategy_pairs.py`
- Modify: `backend/app/quant/registry.py`
- Modify: `backend/app/quant/engine.py` — allow negative weights through to vectorbt

**This is the only strategy that uses shorting.** `spec.allow_short=True`. The engine's `_portfolio_from_weights` may need to permit negative weights (vectorbt does this natively with `from_orders` `size_type="targetpercent"`).

5 fixed pairs from `PAIRS` constant. For each pair, compute the spread `log(A) - β * log(B)` where β is the cointegration coefficient over a rolling lookback. Z-score the spread; long-A short-B when z < -entry, short-A long-B when z > +entry, flat when |z| < exit.

- [ ] **Step 1: Test** (smaller test set since this strategy is complex)

```python
import numpy as np
import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.pairs_trading import PairsTrading


def test_metadata():
    s = PairsTrading()
    assert s.spec.slug == "pairs-trading"
    assert s.spec.category == "classic"
    assert s.spec.universe_kind == "pairs-fixed"
    assert s.spec.allow_short is True
    assert set(s.sweep_grid.keys()) == {"lookback", "entry_z", "exit_z"}


def test_signals_emit_offsetting_long_short_legs():
    """With a stretched spread, the strategy must take *both* sides."""
    s = PairsTrading()
    # Build KO/PEP where KO underperforms PEP by ~5% over the window.
    idx = pd.bdate_range("2026-01-01", periods=150)
    ko = 50.0 * np.linspace(1.0, 0.95, len(idx))    # KO down 5%
    pep = 150.0 * np.linspace(1.0, 1.05, len(idx))  # PEP up 5%
    # The other 8 symbols flat (so the strategy ignores them).
    bars = pd.DataFrame({
        "KO": ko, "PEP": pep,
        "MA": [400.0] * len(idx), "V": [240.0] * len(idx),
        "GOOG": [140.0] * len(idx), "META": [500.0] * len(idx),
        "XOM": [100.0] * len(idx), "CVX": [150.0] * len(idx),
        "JPM": [150.0] * len(idx), "BAC": [30.0] * len(idx),
    }, index=idx)
    w = s.generate_signals(bars, params={"lookback": 60, "entry_z": 2.0, "exit_z": 0.5},
                           ctx=StrategyContext())
    # Late in the series, KO is the underperformer → long KO, short PEP.
    last = w.iloc[-1]
    assert last["KO"] > 0
    assert last["PEP"] < 0
    # Gross exposure roughly matched per pair.
    assert abs(abs(last["KO"]) - abs(last["PEP"])) < 0.05


def test_zero_below_lookback():
    s = PairsTrading()
    idx = pd.bdate_range("2026-01-01", periods=20)
    bars = pd.DataFrame({
        "KO": [50.0] * 20, "PEP": [150.0] * 20,
        "MA": [400.0] * 20, "V": [240.0] * 20,
        "GOOG": [140.0] * 20, "META": [500.0] * 20,
        "XOM": [100.0] * 20, "CVX": [150.0] * 20,
        "JPM": [150.0] * 20, "BAC": [30.0] * 20,
    }, index=idx)
    w = s.generate_signals(bars, params={"lookback": 60, "entry_z": 2.0, "exit_z": 0.5},
                           ctx=StrategyContext())
    assert (w.values == 0).all()
```

- [ ] **Step 2: Implement**

```python
"""Pairs trading — market-neutral long/short on cointegrated pairs.

Five fixed pairs (from app.quant.universe.PAIRS). For each pair (A, B),
compute a rolling-OLS hedge ratio β from log(A) ~ β·log(B), then the
spread = log(A) - β·log(B). Z-score the spread by its rolling mean/std.
Long A, short B when z < -entry. Short A, long B when z > +entry.
Flat when |z| < exit. Equal capital allocation across the 5 pairs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)
from app.quant.universe import PAIRS


def _rolling_beta(log_a: pd.Series, log_b: pd.Series, lookback: int) -> pd.Series:
    """Rolling OLS slope of log_a on log_b."""
    cov = log_a.rolling(lookback).cov(log_b)
    var = log_b.rolling(lookback).var()
    return cov / var.replace(0, np.nan)


class PairsTrading(Strategy):
    spec = StrategySpec(
        slug="pairs-trading",
        name="Pairs Trading",
        category="classic",
        universe_kind="pairs-fixed",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Trades five cointegrated equity pairs (KO/PEP, MA/V, "
            "GOOG/META, XOM/CVX, JPM/BAC). For each pair, the spread "
            "log(A) – β·log(B) is z-scored over a rolling window. When |z| "
            "exceeds the entry threshold the strategy goes long the "
            "underperformer and short the outperformer; positions close "
            "when |z| reverts inside the exit band. Market-neutral by "
            "construction — the only strategy in this lab that shorts."
        ),
        allow_short=True,
    )
    sweep_grid: ParamGrid = {
        "lookback": [30, 60, 90],
        "entry_z": [1.5, 2.0, 2.5],
        "exit_z": [0.0, 0.5],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        lookback = int(params["lookback"])
        entry_z = float(params["entry_z"])
        exit_z = float(params["exit_z"])

        # Capital per pair (5 pairs → 1/5 each side; gross 2/5, net 0).
        legs_per_pair = 1.0 / len(PAIRS)

        weights = pd.DataFrame(0.0, index=bars.index, columns=bars.columns)

        for (a, b) in PAIRS:
            if a not in bars.columns or b not in bars.columns:
                continue
            log_a = np.log(bars[a].replace(0, np.nan))
            log_b = np.log(bars[b].replace(0, np.nan))
            beta = _rolling_beta(log_a, log_b, lookback)
            spread = log_a - beta * log_b
            mu = spread.rolling(lookback).mean()
            sd = spread.rolling(lookback).std()
            z = (spread - mu) / sd.replace(0, np.nan)

            # Stateful entry/exit per pair.
            position = 0   # +1 = long A short B; -1 = short A long B; 0 = flat
            for i in range(len(bars.index)):
                zi = z.iloc[i]
                if pd.isna(zi):
                    continue
                if position == 0:
                    if zi < -entry_z:
                        position = 1     # long A, short B
                    elif zi > entry_z:
                        position = -1    # short A, long B
                else:
                    if abs(zi) < exit_z:
                        position = 0

                if position == 1:
                    weights.iloc[i, weights.columns.get_loc(a)] = legs_per_pair
                    weights.iloc[i, weights.columns.get_loc(b)] = -legs_per_pair
                elif position == -1:
                    weights.iloc[i, weights.columns.get_loc(a)] = -legs_per_pair
                    weights.iloc[i, weights.columns.get_loc(b)] = legs_per_pair
        return weights
```

- [ ] **Step 3: Engine update — verify negative weights flow through**

Check `_portfolio_from_weights` in `backend/app/quant/engine.py`. The `reindex + fillna(0.0)` on weights is fine for negative values, and `vbt.Portfolio.from_orders(... size_type="targetpercent", ...)` accepts negative target percents (vectorbt natively supports shorting). No change needed unless tests reveal an issue. **If T4 of Q1a flagged anything around shorting**, address here.

If `_portfolio_from_weights` clips negative weights anywhere, remove that clip.

- [ ] **Step 4: Register + tests + commit**

```python
from app.quant.strategies.pairs_trading import PairsTrading
```

Insert `PairsTrading(),` into `STRATEGIES`.

Run pairs tests + registry tests + full suite. Expected: 251 passing.

```bash
git add backend/app/quant/strategies/pairs_trading.py backend/app/quant/registry.py backend/tests/test_quant_strategy_pairs.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): pairs-trading (5 cointegrated pairs, market-neutral L/S)

The only strategy with allow_short=True. Uses rolling OLS hedge ratios
to compute spread z-scores per pair, opens market-neutral positions
when |z| > entry, closes when |z| < exit.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: News signal accessor

**Files:**
- Create: `backend/app/quant/news_signal.py`
- Create: `backend/tests/test_quant_news_signal.py`

Pure read-only accessor over the existing `news_articles` + `news_clusters` tables. Produces per-symbol (a) rolling article-count and (b) cluster-level sentiment score over a date window.

**Key design:** The current Phase 3 tables don't tag articles by ticker symbol. The accessor extracts ticker mentions from `news_articles.title + news_articles.summary` using a regex against a passed-in symbol set. (Spec for Q1b: this is "good enough"; a smarter NER pipeline is out of scope.)

- [ ] **Step 1: Test**

```python
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import insert

from app.database import (
    get_engine, news_articles, news_clusters,
)
from app.quant.news_signal import (
    news_coverage_matrix, top_news_universe,
)


def _seed_articles(db, rows):
    with get_engine().begin() as conn:
        conn.execute(insert(news_clusters), rows.get("clusters", []))
        conn.execute(insert(news_articles), rows["articles"])


def test_news_coverage_matrix_counts_per_symbol_per_day(db):
    arts = [
        {"id": "a1", "cluster_id": None, "title": "AAPL beats earnings",
         "summary": "Apple inc beat estimates", "url": "x", "source": "Reuters",
         "published_at": "2026-05-01T10:00:00Z", "category": "finance",
         "image_url": None},
        {"id": "a2", "cluster_id": None, "title": "AAPL up after iPhone reveal",
         "summary": "", "url": "x", "source": "Bloomberg",
         "published_at": "2026-05-01T14:00:00Z", "category": "finance",
         "image_url": None},
        {"id": "a3", "cluster_id": None, "title": "MSFT cloud growth",
         "summary": "Microsoft Azure", "url": "x", "source": "Reuters",
         "published_at": "2026-05-01T11:00:00Z", "category": "finance",
         "image_url": None},
    ]
    _seed_articles(db, {"articles": arts})
    df = news_coverage_matrix(
        symbols=["AAPL", "MSFT", "TSLA"],
        start="2026-05-01", end="2026-05-02",
    )
    # rows = date, columns = symbol, values = article count
    assert df.loc["2026-05-01", "AAPL"] == 2
    assert df.loc["2026-05-01", "MSFT"] == 1
    assert df.loc["2026-05-01", "TSLA"] == 0


def test_top_news_universe_ranks_by_rolling_coverage(db):
    arts = [
        {"id": f"a{i}", "cluster_id": None,
         "title": "AAPL " * 10, "summary": "Apple",
         "url": "x", "source": "Reuters",
         "published_at": f"2026-05-{(i % 5) + 1:02d}T10:00:00Z",
         "category": "finance", "image_url": None}
        for i in range(20)
    ] + [
        {"id": "m1", "cluster_id": None,
         "title": "MSFT cloud", "summary": "Microsoft",
         "url": "x", "source": "Reuters",
         "published_at": "2026-05-03T10:00:00Z",
         "category": "finance", "image_url": None},
    ]
    _seed_articles(db, {"articles": arts})
    top = top_news_universe(
        candidate_symbols=["AAPL", "MSFT", "TSLA", "NVDA"],
        as_of="2026-05-05", lookback_days=7, top_n=2,
    )
    assert top[0] == "AAPL"
    assert "MSFT" in top
```

- [ ] **Step 2: Implement**

```python
"""News-signal accessor for the news-sentiment-momentum strategy.

Reads the dashboard's existing `news_articles` / `news_clusters` tables
(Phase 3). Extracts ticker mentions from article title+summary by simple
substring match against the supplied symbol list — good enough for the
S&P 500 universe; a smarter NER pipeline is out of scope for Q1.
"""

from __future__ import annotations

import re
from datetime import datetime

import pandas as pd
from sqlalchemy import select

from app.database import get_engine, news_articles


_WORD_BOUNDARY = re.compile(r"\b{}\b")


def _load_articles(start: str, end: str) -> pd.DataFrame:
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(news_articles).where(
                (news_articles.c.published_at >= start)
                & (news_articles.c.published_at < end + "T23:59:59Z")
            )
        ).all()
    if not rows:
        return pd.DataFrame(columns=["id", "title", "summary", "published_at"])
    return pd.DataFrame([{
        "id": r.id,
        "title": (r.title or "").upper(),
        "summary": (r.summary or "").upper(),
        "published_at": r.published_at,
    } for r in rows])


def _date_of(published_at: str) -> str:
    return (published_at or "")[:10]


def news_coverage_matrix(
    *, symbols: list[str], start: str, end: str,
) -> pd.DataFrame:
    """Rows = date (ISO yyyy-mm-dd), columns = symbol, values = #articles mentioning."""
    arts = _load_articles(start, end)
    if arts.empty:
        idx = pd.date_range(start, end, freq="D").strftime("%Y-%m-%d")
        return pd.DataFrame(0, index=idx, columns=symbols)

    # Pre-compile regex per symbol — case-insensitive word-boundary match.
    arts["date"] = arts["published_at"].map(_date_of)
    arts["text"] = arts["title"] + " " + arts["summary"]

    out: dict[str, dict[str, int]] = {}
    for sym in symbols:
        pat = re.compile(rf"\b{re.escape(sym)}\b")
        mask = arts["text"].map(lambda t: bool(pat.search(t)))
        sub = arts.loc[mask, ["date"]]
        counts = sub.groupby("date").size().to_dict()
        for d, n in counts.items():
            out.setdefault(d, {})[sym] = int(n)

    idx = pd.date_range(start, end, freq="D").strftime("%Y-%m-%d")
    df = pd.DataFrame(0, index=idx, columns=symbols)
    for d, syms in out.items():
        if d in df.index:
            for sym, n in syms.items():
                df.loc[d, sym] = n
    return df


def top_news_universe(
    *, candidate_symbols: list[str], as_of: str,
    lookback_days: int = 7, top_n: int = 100,
) -> list[str]:
    """Return the `top_n` symbols by rolling article count over the last
    `lookback_days` ending at `as_of` (ISO date). Used by the news-sentiment
    strategy to resolve its `news-top100` universe at runtime."""
    start = (
        datetime.fromisoformat(as_of) - pd.Timedelta(days=lookback_days)
    ).strftime("%Y-%m-%d")
    cov = news_coverage_matrix(symbols=candidate_symbols, start=start, end=as_of)
    if cov.empty:
        return candidate_symbols[:top_n]
    totals = cov.sum(axis=0).sort_values(ascending=False)
    return totals.head(top_n).index.tolist()
```

- [ ] **Step 3: Tests + commit**

```bash
cd backend && /Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -m pytest tests/test_quant_news_signal.py -v
```
Expect: 2 PASS.

Full suite: 253.

```bash
git add backend/app/quant/news_signal.py backend/tests/test_quant_news_signal.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): news_signal accessor — coverage matrix + top_news_universe

Pure read-only over news_articles. Symbol mentions extracted by
word-boundary regex; good enough for S&P 500 names, deferring NER.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Econ signal accessor

**Files:**
- Create: `backend/app/quant/econ_signal.py`
- Create: `backend/tests/test_quant_econ_signal.py`

Read-only accessor over the existing `econ_series` table. Loads the three series the macro-regime overlay needs (`T10Y2Y`, `UNRATE`, `INDPRO`) and exposes a `classify_regime(as_of_date) -> "risk_on" | "risk_off"` function.

- [ ] **Step 1: Test**

```python
import pandas as pd
from sqlalchemy import insert

from app.database import get_engine, econ_series
from app.quant.econ_signal import (
    load_series, classify_regime,
)


def _seed(db, rows):
    with get_engine().begin() as conn:
        conn.execute(insert(econ_series), rows)


def test_load_series_returns_dated_floats(db):
    _seed(db, [
        {"series_id": "T10Y2Y", "date": "2026-01-02", "value": 0.5},
        {"series_id": "T10Y2Y", "date": "2026-01-03", "value": 0.4},
        {"series_id": "T10Y2Y", "date": "2026-01-04", "value": 0.3},
    ])
    s = load_series("T10Y2Y", start="2026-01-01", end="2026-12-31")
    assert isinstance(s, pd.Series)
    assert s.loc["2026-01-02"] == 0.5
    assert len(s) == 3


def test_classify_regime_risk_off_when_yield_curve_inverted(db):
    """Inverted yield curve (T10Y2Y < 0) + rising UNRATE → risk_off."""
    _seed(db, [
        {"series_id": "T10Y2Y", "date": "2026-05-01", "value": -0.3},
        {"series_id": "UNRATE", "date": "2026-04-01", "value": 4.0},
        {"series_id": "UNRATE", "date": "2026-05-01", "value": 4.3},
        {"series_id": "INDPRO", "date": "2026-04-01", "value": 102.0},
        {"series_id": "INDPRO", "date": "2026-05-01", "value": 101.5},
    ])
    regime = classify_regime(as_of="2026-05-15")
    assert regime == "risk_off"


def test_classify_regime_risk_on_when_curve_steep(db):
    _seed(db, [
        {"series_id": "T10Y2Y", "date": "2026-05-01", "value": 1.2},
        {"series_id": "UNRATE", "date": "2026-04-01", "value": 3.8},
        {"series_id": "UNRATE", "date": "2026-05-01", "value": 3.7},
        {"series_id": "INDPRO", "date": "2026-04-01", "value": 101.0},
        {"series_id": "INDPRO", "date": "2026-05-01", "value": 101.5},
    ])
    regime = classify_regime(as_of="2026-05-15")
    assert regime == "risk_on"
```

- [ ] **Step 2: Implement**

```python
"""Econ-signal accessor — macro regime classification from FRED data.

Reads the dashboard's existing `econ_series` table (Phase 2). Exposes:
  - load_series(series_id, start, end) → pd.Series (date-indexed floats)
  - classify_regime(as_of, ...) → "risk_on" | "risk_off"

The macro-regime overlay strategy calls classify_regime to decide whether
to halve gross exposure (risk_off) or stay full-on (risk_on).
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from app.database import econ_series, get_engine


def load_series(series_id: str, *, start: str, end: str) -> pd.Series:
    with get_engine().begin() as conn:
        rows = conn.execute(
            select(econ_series).where(
                (econ_series.c.series_id == series_id)
                & (econ_series.c.date >= start)
                & (econ_series.c.date <= end)
            ).order_by(econ_series.c.date)
        ).all()
    if not rows:
        return pd.Series(dtype="float64", name=series_id)
    return pd.Series(
        {r.date: float(r.value) for r in rows if r.value is not None},
        name=series_id,
    )


def _latest_value_on_or_before(s: pd.Series, as_of: str) -> float | None:
    sub = s[s.index <= as_of]
    if sub.empty:
        return None
    return float(sub.iloc[-1])


def _trend(s: pd.Series, as_of: str, lookback_days: int = 90) -> float | None:
    """Simple slope: (latest – earliest in window) / earliest, NaN if missing."""
    sub = s[s.index <= as_of]
    if len(sub) < 2:
        return None
    cutoff = (pd.Timestamp(as_of) - pd.Timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    sub = sub[sub.index >= cutoff]
    if len(sub) < 2 or sub.iloc[0] == 0:
        return None
    return float(sub.iloc[-1] / sub.iloc[0] - 1.0)


def classify_regime(*, as_of: str, lookback_days: int = 90) -> str:
    """Return 'risk_on' or 'risk_off' based on T10Y2Y, UNRATE, INDPRO."""
    start = (pd.Timestamp(as_of) - pd.Timedelta(days=lookback_days * 4)).strftime("%Y-%m-%d")
    t10y2y = load_series("T10Y2Y", start=start, end=as_of)
    unrate = load_series("UNRATE", start=start, end=as_of)
    indpro = load_series("INDPRO", start=start, end=as_of)

    curve = _latest_value_on_or_before(t10y2y, as_of)
    unrate_trend = _trend(unrate, as_of, lookback_days)
    indpro_trend = _trend(indpro, as_of, lookback_days)

    # Risk-off if: curve inverted OR unemployment rising AND industrial production falling.
    score = 0
    if curve is not None and curve < 0:
        score += 2
    if unrate_trend is not None and unrate_trend > 0:
        score += 1
    if indpro_trend is not None and indpro_trend < 0:
        score += 1

    return "risk_off" if score >= 2 else "risk_on"
```

- [ ] **Step 3: Tests + commit**

Expected total: 256.

```bash
git add backend/app/quant/econ_signal.py backend/tests/test_quant_econ_signal.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): econ_signal accessor — load FRED series + classify_regime

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Fundamentals accessor

**Files:**
- Create: `backend/app/quant/fundamentals.py`
- Create: `backend/tests/test_quant_fundamentals.py`

Thin wrapper around `yfinance.Ticker(...).info` to retrieve P/B and ROE per symbol. File-backed cache (JSON in `backend/data/fundamentals_cache.json`) since `Ticker.info` is slow (~1s per symbol) and the values barely change day-to-day.

- [ ] **Step 1: Test**

```python
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.quant.fundamentals import (
    Fundamentals, get_fundamentals, clear_cache,
)


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_FUNDAMENTALS_CACHE", str(tmp_path / "f.json"))
    clear_cache()
    yield
    clear_cache()


def test_get_fundamentals_uses_yfinance_first_time():
    with patch("app.quant.fundamentals._fetch_yf") as mocked:
        mocked.return_value = {"priceToBook": 5.0, "returnOnEquity": 0.18}
        f = get_fundamentals("AAPL")
    assert isinstance(f, Fundamentals)
    assert f.price_to_book == 5.0
    assert f.roe == 0.18


def test_get_fundamentals_hits_cache_second_time(tmp_path):
    with patch("app.quant.fundamentals._fetch_yf") as mocked:
        mocked.return_value = {"priceToBook": 5.0, "returnOnEquity": 0.18}
        get_fundamentals("AAPL")
        get_fundamentals("AAPL")
        # Cached → only one network call.
        assert mocked.call_count == 1


def test_get_fundamentals_missing_fields_return_none():
    with patch("app.quant.fundamentals._fetch_yf") as mocked:
        mocked.return_value = {}   # yfinance sometimes returns empty
        f = get_fundamentals("XXX")
    assert f.price_to_book is None
    assert f.roe is None


def test_get_fundamentals_batch_uses_one_call_per_uncached():
    with patch("app.quant.fundamentals._fetch_yf") as mocked:
        mocked.return_value = {"priceToBook": 1.0, "returnOnEquity": 0.05}
        out = get_fundamentals_batch(["AAPL", "MSFT"])
        assert mocked.call_count == 2
        assert set(out.keys()) == {"AAPL", "MSFT"}


# Test imports the function used in the batch test
from app.quant.fundamentals import get_fundamentals_batch  # noqa: E402
```

- [ ] **Step 2: Implement**

```python
"""Fundamentals accessor for multi-factor strategy.

Wraps yfinance.Ticker(sym).info — slow and rate-limited — behind a
persistent JSON cache. Cache TTL is effectively "forever" within a run;
the orchestrator can rebuild fundamentals by deleting the cache file.

Used by `multi-factor-combo` strategy for the P/B (value) and ROE
(quality) factors.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Fundamentals:
    symbol: str
    price_to_book: float | None
    roe: float | None


_DEFAULT_CACHE = str(
    Path(__file__).resolve().parent.parent.parent / "data" / "fundamentals_cache.json"
)


def _cache_path() -> Path:
    return Path(os.environ.get("QUANT_FUNDAMENTALS_CACHE", _DEFAULT_CACHE))


def _load_cache() -> dict:
    p = _cache_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def _save_cache(d: dict) -> None:
    p = _cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2))


def clear_cache() -> None:
    p = _cache_path()
    if p.exists():
        p.unlink()


def _fetch_yf(symbol: str) -> dict:
    """Real network call — split out so tests can mock it."""
    return yf.Ticker(symbol).info or {}


def get_fundamentals(symbol: str) -> Fundamentals:
    cache = _load_cache()
    if symbol in cache:
        c = cache[symbol]
        return Fundamentals(
            symbol=symbol,
            price_to_book=c.get("price_to_book"),
            roe=c.get("roe"),
        )
    raw = _fetch_yf(symbol)
    f = Fundamentals(
        symbol=symbol,
        price_to_book=raw.get("priceToBook"),
        roe=raw.get("returnOnEquity"),
    )
    cache[symbol] = {"price_to_book": f.price_to_book, "roe": f.roe}
    _save_cache(cache)
    return f


def get_fundamentals_batch(symbols: list[str]) -> dict[str, Fundamentals]:
    return {sym: get_fundamentals(sym) for sym in symbols}
```

- [ ] **Step 3: Tests + commit**

Expected: 260 passing total.

```bash
git add backend/app/quant/fundamentals.py backend/tests/test_quant_fundamentals.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): fundamentals accessor — file-cached yfinance Ticker.info

Cache lives at backend/data/fundamentals_cache.json (or
QUANT_FUNDAMENTALS_CACHE env var in tests).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: News-sentiment momentum strategy

**Files:**
- Create: `backend/app/quant/strategies/news_sentiment_momentum.py`
- Create: `backend/tests/test_quant_strategy_news_sentiment.py`
- Modify: `backend/app/quant/registry.py`

Uses `ctx.news_clusters` (the populated DataFrame the orchestrator passes). Strategy reads coverage + sentiment, ranks names, longs top decile, rebalances monthly.

- [ ] **Step 1: Test**

```python
import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.news_sentiment_momentum import NewsSentimentMomentum


def test_metadata():
    s = NewsSentimentMomentum()
    assert s.spec.slug == "news-sentiment-momentum"
    assert s.spec.category == "alpha"
    assert s.spec.universe_kind == "news-top100"
    assert set(s.sweep_grid.keys()) == {"sentiment_weight", "lookback_days", "top_pct"}


def test_picks_top_by_combined_score():
    s = NewsSentimentMomentum()
    idx = pd.bdate_range("2026-01-02", periods=80)
    # 5 names; AAA has lots of news with positive sentiment.
    bars = pd.DataFrame({
        "AAA": 100.0, "BBB": 100.0, "CCC": 100.0, "DDD": 100.0, "EEE": 100.0,
    }, index=idx)
    # Coverage DataFrame: date × symbol, values = article counts.
    cov_dates = pd.date_range("2026-01-02", periods=80, freq="D").strftime("%Y-%m-%d")
    coverage = pd.DataFrame(0, index=cov_dates, columns=["AAA", "BBB", "CCC", "DDD", "EEE"])
    coverage["AAA"] = 5
    coverage["BBB"] = 1
    # Sentiment: same shape, in [-1, 1].
    sentiment = pd.DataFrame(0.0, index=cov_dates, columns=["AAA", "BBB", "CCC", "DDD", "EEE"])
    sentiment["AAA"] = 0.7
    sentiment["BBB"] = 0.3
    ctx = StrategyContext()
    ctx.news_clusters = pd.DataFrame({
        # Repurpose this slot to carry both signals. The orchestrator builds it.
    })
    ctx_news = {"coverage": coverage, "sentiment": sentiment}
    # Adapter: strategy expects ctx.news_clusters to have attrs `coverage` and `sentiment`.
    # We pass via setattr for the test.
    setattr(ctx, "_news_signal", ctx_news)
    w = s.generate_signals(
        bars, params={"sentiment_weight": 0.5, "lookback_days": 7, "top_pct": 20},
        ctx=ctx,
    )
    last = w.iloc[-1]
    # AAA should be selected (top by combined score).
    assert last["AAA"] > 0
    # CCC/DDD/EEE have no news → not selected.
    assert last["CCC"] == 0
```

**Note for implementer:** The `StrategyContext` already has a `news_clusters: pd.DataFrame | None` slot. For Q1b we extend the convention: the orchestrator builds a small dict `{"coverage": DataFrame, "sentiment": DataFrame}` and attaches it via `ctx._news_signal = ...` (Python attribute assignment works on dataclasses since `StrategyContext` is non-frozen). The strategy reads `ctx._news_signal`. This keeps the base class stable; if a more formal API is wanted later, refactor.

- [ ] **Step 2: Implement**

```python
"""News-sentiment momentum — long names with highest weighted news score.

Score = (1 - sw) * z(rolling_coverage) + sw * z(rolling_sentiment)

Rebalances monthly. Top `top_pct`% by score equal-weight.
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)


class NewsSentimentMomentum(Strategy):
    spec = StrategySpec(
        slug="news-sentiment-momentum",
        name="News-Sentiment Momentum",
        category="alpha",
        universe_kind="news-top100",
        # The phase-3 news feature went live earlier in this project; the
        # equity curve will be honest about the short live track record.
        inception_date="2026-05-22",
        live_start_date="2026-05-22",
        methodology_blurb=(
            "Each month, rank S&P 500 names by a weighted combination of "
            "rolling news-cluster volume (attention) and average news "
            "sentiment. Long the top decile equal-weight. Uses the news "
            "domain's own ingestion pipeline — the data that powers the "
            "dashboard's Top Stories panel."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "sentiment_weight": [0.3, 0.5, 0.7],
        "lookback_days": [3, 7, 14],
        "top_pct": [5, 10, 20],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        sw = float(params["sentiment_weight"])
        lookback = int(params["lookback_days"])
        top_pct = int(params["top_pct"])

        news_signal = getattr(ctx, "_news_signal", None)
        if not news_signal:
            return pd.DataFrame(0.0, index=bars.index, columns=bars.columns)

        cov = news_signal["coverage"]
        sent = news_signal["sentiment"]
        cov.index = pd.to_datetime(cov.index)
        sent.index = pd.to_datetime(sent.index)
        bars_idx = pd.to_datetime(bars.index)

        # Align to bars index, fill missing with 0.
        cov_aligned = cov.reindex(bars_idx).reindex(columns=bars.columns).fillna(0)
        sent_aligned = sent.reindex(bars_idx).reindex(columns=bars.columns).fillna(0)

        # Rolling sums / means.
        roll_cov = cov_aligned.rolling(lookback, min_periods=1).sum()
        roll_sent = sent_aligned.rolling(lookback, min_periods=1).mean()

        # Cross-sectional z-scores per row.
        def _z(df: pd.DataFrame) -> pd.DataFrame:
            mu = df.mean(axis=1)
            sd = df.std(axis=1).replace(0, 1.0)
            return df.sub(mu, axis=0).div(sd, axis=0)

        score = (1 - sw) * _z(roll_cov) + sw * _z(roll_sent)

        # Monthly rebalance on the last business day of each month.
        month_periods = bars_idx.to_period("M")
        last_per_month = pd.Series(bars_idx, index=bars_idx).groupby(month_periods).max()
        rebal_set = set(last_per_month.values)

        weights = pd.DataFrame(0.0, index=bars.index, columns=bars.columns)
        winners: list[str] = []
        for i, day in enumerate(bars_idx):
            if day in rebal_set:
                row = score.iloc[i].dropna()
                if not row.empty:
                    n_pick = max(1, int(len(row) * top_pct / 100))
                    winners = row.sort_values(ascending=False).head(n_pick).index.tolist()
            if winners:
                w = 1.0 / len(winners)
                for sym in winners:
                    weights.iloc[i, weights.columns.get_loc(sym)] = w
        return weights
```

- [ ] **Step 3: Register + tests + commit**

```python
from app.quant.strategies.news_sentiment_momentum import NewsSentimentMomentum
```

Insert `NewsSentimentMomentum(),` into `STRATEGIES` (category="alpha" → before benchmark).

Expected total: 263.

```bash
git add backend/app/quant/strategies/news_sentiment_momentum.py backend/app/quant/registry.py backend/tests/test_quant_strategy_news_sentiment.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): news-sentiment-momentum alpha strategy

Reads news coverage + sentiment from ctx._news_signal (populated by
the orchestrator from the existing news_articles table).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Macro-regime overlay strategy

**Files:**
- Create: `backend/app/quant/strategies/macro_regime_overlay.py`
- Create: `backend/tests/test_quant_strategy_macro_regime.py`
- Modify: `backend/app/quant/registry.py`

Wraps the cross-sectional momentum signal but reads `ctx._regime` (a `pd.Series` of regime labels by date — populated by the orchestrator). When `risk_off`, halves the per-name weight or rotates into defensives.

- [ ] **Step 1: Test**

```python
import pandas as pd

from app.quant.strategies.base import StrategyContext
from app.quant.strategies.macro_regime_overlay import MacroRegimeOverlay


def test_metadata():
    s = MacroRegimeOverlay()
    assert s.spec.slug == "macro-regime-overlay"
    assert s.spec.category == "alpha"
    assert s.spec.universe_kind == "sp500"
    assert set(s.sweep_grid.keys()) == {"lookback", "skip", "top_pct", "defensive_rotation"}


def test_halves_exposure_in_risk_off():
    s = MacroRegimeOverlay()
    idx = pd.bdate_range("2024-01-02", periods=300)
    import numpy as np
    data = {f"S{i:02d}": 100.0 * (1 + 0.0001 * i) ** np.arange(len(idx)) for i in range(20)}
    bars = pd.DataFrame(data, index=idx)
    # Risk-off regime for the last 60 days.
    regime = pd.Series("risk_on", index=idx.strftime("%Y-%m-%d"))
    regime.iloc[-60:] = "risk_off"
    ctx = StrategyContext()
    setattr(ctx, "_regime", regime)
    w_risk_off = s.generate_signals(
        bars, params={"lookback": 9, "skip": 1, "top_pct": 10, "defensive_rotation": False},
        ctx=ctx,
    )
    # Gross exposure at the last bar should be ~0.5 (half of full investment).
    gross = w_risk_off.iloc[-1].abs().sum()
    assert 0.3 < gross < 0.6
```

- [ ] **Step 2: Implement**

```python
"""Macro-regime overlay — momentum sized down in risk-off regimes.

Wraps the same cross-sectional momentum signal as CrossSectionalMomentum,
but reads a per-day regime label from ctx._regime (Series of date→str)
and halves gross exposure (or rotates to defensives) when risk_off.
"""

from __future__ import annotations

import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)
from app.quant.strategies.cross_sectional_momentum import (
    CrossSectionalMomentum, _monthly_rebalance_weights,
)

_DEFENSIVES = ("XLP", "XLU", "XLV")


class MacroRegimeOverlay(Strategy):
    spec = StrategySpec(
        slug="macro-regime-overlay",
        name="Macro-Regime Overlay (Momentum)",
        category="alpha",
        universe_kind="sp500",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Same Jegadeesh-Titman 12-1 momentum top-decile selection as "
            "the classic cross-sectional momentum strategy, but with a "
            "FRED-derived macro regime overlay. When the yield curve "
            "inverts and unemployment is rising (risk_off), the strategy "
            "halves gross exposure — and optionally rotates the residual "
            "into defensive sectors (XLP/XLU/XLV) — to dampen drawdowns "
            "during recessionary regimes."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "lookback": [6, 9, 12],
        "skip": [0, 1],
        "top_pct": [5, 10],
        "defensive_rotation": [False, True],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        # Re-use CrossSectionalMomentum's compute path.
        base_params = {
            "lookback": params["lookback"],
            "skip": params["skip"],
            "top_pct": params["top_pct"],
        }
        base = CrossSectionalMomentum().generate_signals(bars, base_params, ctx)

        regime = getattr(ctx, "_regime", None)
        if regime is None:
            return base

        defensive = bool(params.get("defensive_rotation", False))

        idx_dates = pd.to_datetime(bars.index).strftime("%Y-%m-%d")
        regime_aligned = regime.reindex(idx_dates, method="ffill").fillna("risk_on")

        out = base.copy()
        for i, day in enumerate(idx_dates):
            if regime_aligned.iloc[i] == "risk_off":
                out.iloc[i] = out.iloc[i] * 0.5
                if defensive:
                    # Move the freed half into defensives if present in the universe.
                    available_def = [d for d in _DEFENSIVES if d in out.columns]
                    if available_def:
                        per = 0.5 / len(available_def)
                        for d in available_def:
                            out.iloc[i, out.columns.get_loc(d)] = per
        return out
```

- [ ] **Step 3: Register + tests + commit**

```python
from app.quant.strategies.macro_regime_overlay import MacroRegimeOverlay
```

Insert into `STRATEGIES`. Expected total: 265.

```bash
git add backend/app/quant/strategies/macro_regime_overlay.py backend/app/quant/registry.py backend/tests/test_quant_strategy_macro_regime.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): macro-regime-overlay alpha strategy

Wraps cross-sectional momentum + reads ctx._regime to halve exposure
(or rotate to XLP/XLU/XLV) in risk_off regimes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Multi-factor combo strategy

**Files:**
- Create: `backend/app/quant/strategies/multi_factor_combo.py`
- Create: `backend/tests/test_quant_strategy_multi_factor.py`
- Modify: `backend/app/quant/registry.py`

Reads `ctx.fundamentals` (dict of `symbol → Fundamentals(price_to_book, roe)`) plus computes momentum + low-vol from bars. Composite z-score; long top decile monthly.

- [ ] **Step 1: Test**

```python
import numpy as np
import pandas as pd

from app.quant.fundamentals import Fundamentals
from app.quant.strategies.base import StrategyContext
from app.quant.strategies.multi_factor_combo import MultiFactorCombo


def test_metadata():
    s = MultiFactorCombo()
    assert s.spec.slug == "multi-factor-combo"
    assert s.spec.category == "alpha"
    assert s.spec.universe_kind == "sp500"
    grid = s.sweep_grid
    assert {"w_momentum", "w_value", "w_quality", "w_lowvol", "top_pct"} == set(grid.keys())


def test_uses_fundamentals_from_ctx():
    s = MultiFactorCombo()
    idx = pd.bdate_range("2024-01-02", periods=300)
    data = {f"S{i:02d}": 100.0 * (1 + 0.0001 * i) ** np.arange(len(idx)) for i in range(20)}
    bars = pd.DataFrame(data, index=idx)
    ctx = StrategyContext()
    # Give S19 the best (lowest) P/B and (highest) ROE.
    ctx.fundamentals = {
        sym: Fundamentals(symbol=sym, price_to_book=20.0 - i, roe=0.01 * i)
        for i, sym in enumerate(bars.columns)
    }
    w = s.generate_signals(
        bars, params={"w_momentum": 1.0, "w_value": 1.0, "w_quality": 1.0, "w_lowvol": 1.0,
                       "top_pct": 10},
        ctx=ctx,
    )
    # S19 has best fundamentals AND highest momentum drift → selected.
    assert w.iloc[-1]["S19"] > 0


def test_zero_when_fundamentals_missing():
    s = MultiFactorCombo()
    idx = pd.bdate_range("2024-01-02", periods=300)
    bars = pd.DataFrame({"AAA": [100.0] * len(idx)}, index=idx)
    ctx = StrategyContext()
    ctx.fundamentals = {}
    w = s.generate_signals(
        bars, params={"w_momentum": 1.0, "w_value": 1.0, "w_quality": 1.0, "w_lowvol": 1.0,
                       "top_pct": 10},
        ctx=ctx,
    )
    assert (w.values == 0).all()
```

- [ ] **Step 2: Implement**

```python
"""Multi-factor combo — z-score blend of momentum, value, quality, low-vol.

Score = w_m·z(12-1 mom) + w_v·z(-P/B) + w_q·z(ROE) + w_lv·z(-σ)

Long top-decile by score, monthly rebalance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.quant.strategies.base import (
    ParamGrid, Strategy, StrategyContext, StrategySpec,
)

_DAYS_PER_MONTH = 21
_MOMENTUM_LOOKBACK_M = 12
_SKIP_M = 1
_VOL_LOOKBACK_D = 60


def _cs_z(series: pd.Series) -> pd.Series:
    mu = series.mean()
    sd = series.std()
    if sd == 0 or np.isnan(sd):
        return pd.Series(0.0, index=series.index)
    return (series - mu) / sd


class MultiFactorCombo(Strategy):
    spec = StrategySpec(
        slug="multi-factor-combo",
        name="Multi-Factor Combo",
        category="alpha",
        universe_kind="sp500",
        inception_date="2015-01-02",
        live_start_date="2025-01-02",
        methodology_blurb=(
            "Each month, score every S&P 500 name as a weighted z-score "
            "combination of four factors: 12-1 momentum, value (-price/"
            "book), quality (return on equity), and low-volatility "
            "(-60-day realized σ). Go long the top decile equal-weight. "
            "A classic four-factor portfolio."
        ),
        allow_short=False,
    )
    sweep_grid: ParamGrid = {
        "w_momentum": [0.0, 0.5, 1.0],
        "w_value":    [0.0, 0.5, 1.0],
        "w_quality":  [0.0, 0.5, 1.0],
        "w_lowvol":   [0.0, 0.5, 1.0],
        "top_pct":    [5, 10],
    }

    def generate_signals(
        self,
        bars: pd.DataFrame,
        params: dict,
        ctx: StrategyContext,
    ) -> pd.DataFrame:
        if not ctx.fundamentals:
            return pd.DataFrame(0.0, index=bars.index, columns=bars.columns)

        wm = float(params["w_momentum"])
        wv = float(params["w_value"])
        wq = float(params["w_quality"])
        wlv = float(params["w_lowvol"])
        top_pct = int(params["top_pct"])

        lookback_d = _MOMENTUM_LOOKBACK_M * _DAYS_PER_MONTH
        skip_d = _SKIP_M * _DAYS_PER_MONTH
        warmup = lookback_d + skip_d
        if len(bars) < warmup:
            return pd.DataFrame(0.0, index=bars.index, columns=bars.columns)

        # Per-day cross-sectional factors.
        momentum = (bars.shift(skip_d) / bars.shift(skip_d + lookback_d)) - 1.0
        volatility = bars.pct_change().rolling(_VOL_LOOKBACK_D).std()

        # Static fundamental factors per name (point-in-time approximation).
        pb_series = pd.Series({
            sym: ctx.fundamentals[sym].price_to_book
            for sym in bars.columns if sym in ctx.fundamentals
        })
        roe_series = pd.Series({
            sym: ctx.fundamentals[sym].roe
            for sym in bars.columns if sym in ctx.fundamentals
        })

        weights = pd.DataFrame(0.0, index=bars.index, columns=bars.columns)
        bars_idx = pd.to_datetime(bars.index)
        month_periods = bars_idx.to_period("M")
        last_per_month = pd.Series(bars_idx, index=bars_idx).groupby(month_periods).max()
        rebal_set = set(last_per_month.values)
        winners: list[str] = []

        for i, day in enumerate(bars_idx):
            if day in rebal_set and i >= warmup:
                mom_row = momentum.iloc[i].dropna()
                vol_row = volatility.iloc[i].dropna()
                common = mom_row.index.intersection(vol_row.index)\
                                       .intersection(pb_series.index)\
                                       .intersection(roe_series.index)
                if common.empty:
                    continue
                z_mom = _cs_z(mom_row.loc[common])
                z_val = _cs_z(-pb_series.loc[common].astype(float).dropna())
                z_qual = _cs_z(roe_series.loc[common].astype(float).dropna())
                z_lv = _cs_z(-vol_row.loc[common])
                z_val = z_val.reindex(common, fill_value=0)
                z_qual = z_qual.reindex(common, fill_value=0)
                score = wm * z_mom + wv * z_val + wq * z_qual + wlv * z_lv
                n_pick = max(1, int(len(score) * top_pct / 100))
                winners = score.sort_values(ascending=False).head(n_pick).index.tolist()
            if winners:
                w = 1.0 / len(winners)
                for sym in winners:
                    if sym in weights.columns:
                        weights.iloc[i, weights.columns.get_loc(sym)] = w
        return weights
```

- [ ] **Step 3: Register + tests + commit**

```python
from app.quant.strategies.multi_factor_combo import MultiFactorCombo
```

Insert into `STRATEGIES`. Expected total: 268.

```bash
git add backend/app/quant/strategies/multi_factor_combo.py backend/app/quant/registry.py backend/tests/test_quant_strategy_multi_factor.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant): multi-factor-combo alpha strategy

Z-score blend: momentum + (-P/B) + ROE + (-σ). Top-decile monthly.
Reads ctx.fundamentals (built by orchestrator from yfinance Ticker.info
through the file-cached app.quant.fundamentals accessor).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: Wire StrategyContext in the orchestrator

**Files:**
- Modify: `backend/app/quant/orchestration.py`
- Create: `backend/tests/test_quant_orchestration_alpha.py`

The orchestrator needs to build the `StrategyContext` correctly per strategy. Today it passes a default empty context. After this task:

- For `news-sentiment-momentum`: builds `coverage` + `sentiment` DataFrames from `news_signal.news_coverage_matrix` and a simple "0 = neutral" placeholder for sentiment (sentiment scoring isn't in Phase 3 yet — pass zeros; the strategy still benefits from coverage).
- For `macro-regime-overlay`: builds a Series of `risk_on`/`risk_off` labels by date using `econ_signal.classify_regime`.
- For `multi-factor-combo`: builds `ctx.fundamentals` by calling `fundamentals.get_fundamentals_batch(symbols)`.

Strategies that don't need context (the 6 non-alpha ones) get an empty `StrategyContext()` — no change.

- [ ] **Step 1: Test**

```python
import json
from sqlalchemy import insert, select

from app.database import econ_series, get_engine, news_articles, strategy_runs
from app.quant.bars import upsert_bars
from app.quant.orchestration import inception_walkforward
from app.quant.strategies.macro_regime_overlay import MacroRegimeOverlay
from app.quant.strategies.news_sentiment_momentum import NewsSentimentMomentum

# Helper to seed minimal data so the orchestrator doesn't bail on "no bars".


def _seed_minimal(years: int = 5):
    import pandas as pd
    idx = pd.bdate_range("2020-01-02", periods=252 * years)
    for sym in ["SPY", "AAPL", "MSFT"]:
        df = pd.DataFrame({
            "Open": 100.0, "High": 101.0, "Low": 99.0,
            "Close": 100.0, "Adj Close": 100.0, "Volume": 1_000_000,
        }, index=idx)
        upsert_bars(sym, df)


def test_news_sentiment_orchestrator_populates_news_signal_ctx(db):
    _seed_minimal()
    # Seed a few news articles so the accessor has data.
    with get_engine().begin() as conn:
        conn.execute(insert(news_articles), [
            {"id": "a1", "cluster_id": None, "title": "AAPL beats",
             "summary": "", "url": "x", "source": "Reuters",
             "published_at": "2024-12-01T10:00:00Z",
             "category": "finance", "image_url": None},
        ])
    s = NewsSentimentMomentum()
    # Orchestrator must not crash + must mark the run success.
    run_id = inception_walkforward(s, train_years=2, test_years=1, step_months=6,
                                    initial_equity=100_000)
    with get_engine().begin() as conn:
        row = conn.execute(
            select(strategy_runs).where(strategy_runs.c.id == run_id)
        ).first()
    assert row.status == "success"


def test_macro_regime_orchestrator_populates_regime_ctx(db):
    _seed_minimal()
    with get_engine().begin() as conn:
        conn.execute(insert(econ_series), [
            {"series_id": "T10Y2Y", "date": "2024-06-01", "value": -0.3},
            {"series_id": "UNRATE",  "date": "2024-05-01", "value": 4.0},
            {"series_id": "UNRATE",  "date": "2024-06-01", "value": 4.2},
            {"series_id": "INDPRO",  "date": "2024-05-01", "value": 100.0},
            {"series_id": "INDPRO",  "date": "2024-06-01", "value": 99.0},
        ])
    s = MacroRegimeOverlay()
    run_id = inception_walkforward(s, train_years=2, test_years=1, step_months=6,
                                    initial_equity=100_000)
    with get_engine().begin() as conn:
        row = conn.execute(
            select(strategy_runs).where(strategy_runs.c.id == run_id)
        ).first()
    assert row.status == "success"
```

- [ ] **Step 2: Modify `orchestration.py`**

Add a `_build_context` helper and call it where `run_grid` and `run_single` are invoked. Sketch (you'll integrate at the top of `inception_walkforward` and pass `ctx` through):

```python
from app.quant import econ_signal, news_signal
from app.quant.fundamentals import get_fundamentals_batch
from app.quant.strategies.base import StrategyContext


def _build_context(
    strategy: "Strategy",
    bars: pd.DataFrame,
    *,
    universe_symbols: list[str],
) -> StrategyContext:
    ctx = StrategyContext()
    slug = strategy.spec.slug

    if slug == "news-sentiment-momentum":
        start = bars.index[0].strftime("%Y-%m-%d")
        end = bars.index[-1].strftime("%Y-%m-%d")
        coverage = news_signal.news_coverage_matrix(
            symbols=universe_symbols, start=start, end=end,
        )
        # No sentiment column in Phase 3 yet — pass zeros.
        sentiment = pd.DataFrame(0.0, index=coverage.index, columns=coverage.columns)
        setattr(ctx, "_news_signal", {"coverage": coverage, "sentiment": sentiment})

    elif slug == "macro-regime-overlay":
        # Build per-day regime over bars range. Cheap to compute daily; the
        # underlying FRED series are low frequency, so most days will repeat.
        dates = bars.index.strftime("%Y-%m-%d")
        labels = []
        for d in dates:
            labels.append(econ_signal.classify_regime(as_of=d))
        regime = pd.Series(labels, index=dates)
        setattr(ctx, "_regime", regime)

    elif slug == "multi-factor-combo":
        # Cache-backed; pulls from disk for repeat symbols.
        ctx.fundamentals = get_fundamentals_batch(universe_symbols)

    return ctx
```

Then in `inception_walkforward`, after `bars = load_close_matrix(...)`:
```python
ctx = _build_context(strategy, bars, universe_symbols=symbols)
```
…and pass `ctx=ctx` to both `run_grid` and `run_single`.

Make sure `run_grid` and `run_single` already accept a `ctx` kwarg (they do — Q1a Task 14/15).

- [ ] **Step 3: Run all orchestration tests + full suite + commit**

```bash
cd backend && /Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -m pytest tests/test_quant_orchestration.py tests/test_quant_orchestration_alpha.py -v
```
All pass.

Full suite ~270.

```bash
git add backend/app/quant/orchestration.py backend/tests/test_quant_orchestration_alpha.py
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant/orchestration): build StrategyContext for alpha strategies

News-sentiment gets {coverage, sentiment} matrices via news_signal.
Macro-regime gets a per-day risk_on/risk_off Series via econ_signal.
Multi-factor gets ctx.fundamentals via the cached yfinance accessor.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Smoke test all 9 strategies against real data

Manual verification — not TDD. Run each strategy's inception walk-forward against real yfinance data and confirm sensible results.

- [ ] **Step 1: Fetch S&P 500 + pair + defensive bars**

```bash
/Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -c "
from app.database import init_db
from app.quant.bars import fetch_and_cache
from app.quant.universe import SP500_SYMBOLS
init_db()
# Already-cached: SPY (from Q1a). Add the rest of the universe + defensives.
symbols = sorted(set(SP500_SYMBOLS) | {'SPY', 'XLP', 'XLU', 'XLV'})
n = fetch_and_cache(symbols, start='2018-01-02', end='2025-01-02')
print(f'wrote {n} rows for {len(symbols)} symbols')
"
```
Expected: writes hundreds of thousands of rows. May take 5–15 minutes due to yfinance throttling. Set Bash timeout to 1200000 (20 min).

- [ ] **Step 2: Run each remaining strategy's walk-forward**

```bash
/Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -c "
from app.database import init_db
from app.quant.orchestration import inception_walkforward
from app.quant.registry import STRATEGIES
init_db()
for s in STRATEGIES:
    if s.spec.slug in ('buy-hold-spy', 'sma-crossover'):
        continue   # Already smoke-tested in Q1a.
    print(f'>>> Running {s.spec.slug}')
    try:
        rid = inception_walkforward(s, train_years=3, test_years=1, step_months=6)
        print(f'    OK run_id={rid}')
    except Exception as e:
        print(f'    FAILED: {e}')
"
```
Expected: each strategy succeeds. The S&P-500-wide strategies (`rsi`, `xs_momentum`, `multi-factor`, `macro-regime`) are the heavy hitters — each may take 1–3 minutes. Total ~20 min. Set Bash timeout to 1800000 (30 min).

- [ ] **Step 3: Inspect leaderboard**

```bash
/Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -c "
import json
from sqlalchemy import select
from app.database import init_db, get_engine, strategy_runs
init_db()
with get_engine().begin() as conn:
    rows = conn.execute(
        select(strategy_runs.c.strategy_slug, strategy_runs.c.status, strategy_runs.c.summary_metrics)
        .order_by(strategy_runs.c.id.desc())
    ).all()
seen = set()
for slug, status, summary in rows:
    if slug in seen:
        continue
    seen.add(slug)
    if summary:
        m = json.loads(summary)
        print(f'{slug:32s} status={status} tot={m.get(\"total_return\",0):.2%} sharpe={m.get(\"sharpe\",0):.2f} dd={m.get(\"max_drawdown\",0):.2%}')
    else:
        print(f'{slug:32s} status={status} (no summary)')
"
```

Expected: all 9 strategies show `status=success` with sensible metrics. Sharpe ratios in [-0.5, 2.0], drawdowns in [-50%, 0%], total returns wildly varying. Pairs trading should show much lower correlation to SPY than the others (market-neutral). News-sentiment will have very short history since `inception_date="2026-05-22"` — that's expected, just confirm it didn't crash.

- [ ] **Step 4: If anything failed, debug + small fix commits**

Common possible issues:
- Cross-sectional momentum / multi-factor on Python 3.14: pandas DataFrame.iloc setting with column-position indexing has gotten stricter; if seen, switch to `.loc` or `df.at`.
- News-sentiment with inception=live_start: walk-forward will refuse (0 windows); this is expected, the strategy just produces an empty summary. Confirm `status` is still `success` (the orchestrator's failure path requires a raise, which it shouldn't).
- Multi-factor's first run will fetch 500 fundamentals from yfinance — slow (~10 min). The cache file fills as it goes.

Fix anything that's actually broken; commit fixes as small, focused commits.

---

## Self-review

**Spec coverage** (mapping plan tasks → spec §5):
- §5.1 strategy #2 RSI mean-reversion → Task 3
- §5.1 strategy #3 Cross-sectional momentum → Task 4
- §5.1 strategy #4 Pairs trading → Task 5
- §5.1 strategy #5 Bollinger breakout → Task 2 (done before RSI for warm-up — SPY single-name, simplest)
- §5.2 strategy #7 News-sentiment momentum → Tasks 6 (accessor) + 9 (strategy)
- §5.2 strategy #8 Macro-regime overlay → Tasks 7 (accessor) + 10 (strategy)
- §5.2 strategy #9 Multi-factor combo → Tasks 8 (fundamentals accessor) + 11 (strategy)
- §4.4 cost model uniformity (allow_short for pairs) → Tasks 1 (helper) + 5 (only short strategy)
- Orchestrator context wiring → Task 12
- End-to-end smoke verification → Task 13

**Placeholder scan:** no TBDs, no "implement later" — every step has actual code.

**Type consistency:**
- `StrategyContext` uses `news_clusters`, `econ_series`, `fundamentals` (the base class fields). The dashboard-integrated strategies attach extra payload via `ctx._news_signal` and `ctx._regime` as deliberate Python attribute assignments — documented in Task 9's note. `fundamentals` is the base-class field (used directly by Task 11).
- `Fundamentals` dataclass field names (`price_to_book`, `roe`) match between Task 8 (definition) and Task 11 (consumer).
- `CrossSectionalMomentum._monthly_rebalance_weights` is the helper reused by `MacroRegimeOverlay`.

**Performance budget for the full smoke:** Task 13 step 1 fetches ~500 symbols × ~1750 days ≈ 850k rows. yfinance throttles → realistic 5–15 min. Steps 2 takes another ~20 min across 7 walk-forwards. The full smoke is ~30–40 min. Acceptable — runs once.

**Out of scope held:** no HTTP routes, no scheduler jobs, no forward-step loop, no frontend.
