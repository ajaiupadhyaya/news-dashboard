# Quant Lab — Design Spec

**Date:** 2026-05-22
**Phase:** Q1 (Backtest Engine). Q2 (live paper, daily), Q3 (intraday backtests), Q4 (live intraday) follow as separate specs.
**Status:** Draft → pending user review

---

## 1. Goal

Add a fifth first-class domain to the news-dashboard — **Quant Lab** at `/quant` — that demonstrates real quantitative-trading methodology by running a suite of strategies against the S&P 500, with full-rigor backtest validation and a continuously-extending, deterministic "live" track record.

**Audience:** the owner (auth-gated, same as the rest of the dashboard). The page is a personal lab + portfolio-quality showcase the owner can share by password.

**Q1 success looks like:** opening `/quant` shows nine strategies, each with a real growing equity curve, full tear-sheet metrics, walk-forward windows, and a parameter sweep heatmap. New trading days extend the curve automatically each night.

## 2. Non-goals (Q1)

- Live execution against the real Alpaca paper account — Q2.
- Intraday bars / streaming — Q3 + Q4.
- Custom strategy authoring via the UI — strategies are added as Python files.
- Public access / share links — auth-gated like the rest of the dashboard.
- Shorting except for the pairs-trading strategy.
- Leverage, margin modeling, or options.

## 3. Decisions made in brainstorm (2026-05-22)

| # | Decision | Rationale |
|---|---|---|
| 1 | Equal billing: backtests + live-paper as first-class. **Q1 = backtest engine first.** | User wants both eventually; backtests deliver value immediately without waiting for live PnL to accumulate. |
| 2 | Auth-gated, single-user. | Matches rest of dashboard. Shareable by password. |
| 3 | 9 strategies: 6 classics + 3 dashboard-integrated. | Strong narrative; integration with news/macro data showcases the project as a whole. |
| 4 | `vectorbt` engine, custom strategies. | Vectorized grid sweeps + rich built-in metrics. Strategies (the interesting part) stay user-written. |
| 5 | Intraday-first eventually; **Q1 is daily-only**. | Phased decomposition keeps Q1 shippable. Daily is sufficient for showcase. |
| 6 | Full-rigor methodology: train/test split, walk-forward, parameter sweep, realistic costs, benchmark. | Single biggest "shows quant understanding" dial. |
| 7 | Universe: **S&P 500**. | Most interesting cross-sectional results; tractable with vectorbt. |
| 8 | **Continuous daily forward-step**: re-run each strategy at market close, append one day to the persistent equity curve. | Real growing "live track record" without needing Alpaca yet. |
| 9 | Bento `/quant` home + `/quant/strategy/:slug` detail. Matches `/finance`, `/economics`. | Reuses existing `BentoGrid`, `Breadcrumb`, `Panel`, `LineChart`, `ChartControls`, ⌘K palette. |
| 10 | Methodology blurb on detail page; **no source code shown**. | Cleaner presentation, less developer-y, easier to share. |

## 4. Architecture

### 4.1 Directory layout

```
backend/app/
├── quant/                          ← new package
│   ├── strategies/
│   │   ├── base.py                 ← Strategy ABC + result types
│   │   ├── sma_crossover.py
│   │   ├── rsi_mean_reversion.py
│   │   ├── cross_sectional_momentum.py
│   │   ├── pairs_trading.py
│   │   ├── bollinger_breakout.py
│   │   ├── buy_hold_spy.py
│   │   ├── news_sentiment_momentum.py
│   │   ├── macro_regime_overlay.py
│   │   └── multi_factor_combo.py
│   ├── registry.py                 ← STRATEGIES list + metadata
│   ├── universe.py                 ← versioned S&P 500 constituents + pair lists
│   ├── bars.py                     ← daily bar warehouse (fetch / cache / read)
│   ├── engine.py                   ← vectorbt wrapper + walk-forward harness
│   ├── runner.py                   ← daily forward-step loop (continuous mode)
│   └── metrics.py                  ← tear-sheet metrics (vectorbt + quantstats)
├── routes/quant.py                 ← /api/quant/* routes
├── services/quant_service.py       ← orchestration
└── models.py                       ← + BarCache, Strategy, StrategyRun,
                                      EquityPoint, SimulatedTrade, Position

frontend/src/quant/                 ← new domain folder
├── (components, hooks)
frontend/src/routes/
├── QuantRoute.tsx                  ← /quant bento home
└── StrategyRoute.tsx               ← /quant/strategy/:slug detail
```

### 4.2 Two compute paths

**A) Inception walk-forward backtest** — one-shot per strategy, triggered when:
- the strategy is added,
- the sweep grid or `inception_date` changes,
- or the user clicks **Recompute backtest**.

Runs as a background asyncio task; status tracked on the `StrategyRun` row so the UI can poll.

```
inception_walkforward(strategy):
    bars = bars.load(strategy.universe, from=inception_date, to=live_start_date)
    windows = build_walkforward_windows(
        bars.dates, train_years=3, test_years=1, step_months=6
    )
    sweep_results, walkforward_results = {}, []
    for window in windows:
        train_metrics = engine.run_grid(strategy, bars[window.train], strategy.sweep_grid)
        best_params = argmax(train_metrics, key="sharpe")
        oos_result = engine.run_single(strategy, bars[window.test], best_params)
        walkforward_results.append({window, best_params, oos_metrics: oos_result.metrics})
        merge(sweep_results, train_metrics)

    stitched_equity = stitch_oos_windows(walkforward_results)
    persist:
        StrategyRun row (summary_metrics, walkforward_windows, param_sweep)
        EquityPoint rows for stitched curve     (phase="backtest")
        SimulatedTrade rows for stitched trades (phase="backtest")
    update Strategy.chosen_params = most_recent_window.best_params
```

**Key call:** the displayed backtest curve is the **stitched OOS curve**, not an in-sample fit. The parameter-sweep heatmap shows averaged in-sample Sharpe — useful for visualizing the response surface without misrepresenting it as performance.

**B) Continuous forward-step** — APScheduler job `forward_step_all_strategies`, scheduled ~21:30 ET (after market close, after yfinance has the day's bar). Extends every enabled strategy's equity curve by exactly one day.

```
forward_step(strategy, target_date):
    if strategy.last_forward_step_date >= target_date: return     # idempotent

    bars = bars.load(strategy.universe, from=target_date - lookback_buffer, to=target_date)
    signals_today = strategy.generate_signals(bars, ctx).loc[target_date]   # no peeking

    target_positions = portfolio.size(signals_today, current_equity, cost_model)
    fills = engine.simulate_fills(
        current_positions=Position.load(strategy),
        target_positions=target_positions,
        bars=bars.loc[target_date],
        slippage_bps=cost_model.slippage_bps,
    )
    new_equity = mark_to_market(positions_after_fills, bars.loc[target_date])

    transaction:
        write SimulatedTrade rows for `fills` (phase="forward")
        upsert Position rows
        insert EquityPoint(date=target_date, equity=new_equity, phase="forward")
        update Strategy.last_forward_step_date = target_date

    log structured event {strategy_slug, fill_count, daily_return}
```

**Catch-up on resume:** if Fly was down or a holiday created a gap, the job loops `forward_step` from `last_forward_step_date + 1` up to today's date — each step is independent and idempotent. Bounded to a max of 30 days per run; logs a warning + exits if longer.

**Bar refresh:** separate `warm_bars` APScheduler job at ~21:00 ET refreshes `bar_cache` for the universe in ~50-symbol yfinance batches. The forward-step job depends on this completing first.

### 4.3 Engine, concretely

- `engine.run_grid(strategy, bars, grid) -> DataFrame[params, metrics]` — `vbt.Portfolio.from_signals` across the full parameter grid in one vectorized call.
- `engine.run_single(strategy, bars, params) -> Result` — same, single parameter tuple. Used for OOS evaluation and forward-step "evaluate today".
- `engine.simulate_fills(...)` — thin custom function for the forward-step path; mirrors the same cost model so backtest and forward stay numerically consistent. (vectorbt is for batch backtests, not single-step execution.)
- `quantstats` for tear-sheet metrics (Sharpe, Sortino, Calmar, Omega, max DD, monthly return matrix, rolling Sharpe). Returns plain dicts/Series; frontend renders with its own D3.

### 4.4 Cost model (uniform across strategies)

- Commission: $0 (Alpaca-style)
- Slippage: 5 bps per side on entry and exit
- No shorting **except** in `pairs-trading`
- Starting equity: notional **$100,000** per strategy
- Position sizing: equal-weight across active positions unless the strategy overrides

## 5. Strategies (9)

Each strategy declares `slug`, `name`, `category`, `universe`, `parameters` (with sweep grid for inception walk-forward), `inception_date`, `live_start_date`, `methodology_blurb`, and implements `Strategy.generate_signals(bars, ctx) -> signals_df`. The engine handles portfolio construction, costs, and metrics uniformly.

### 5.1 Classics (6)

| # | Slug | Universe | Signal | Sweep grid | Notes |
|---|---|---|---|---|---|
| 1 | `sma-crossover` | SPY | Long when fast-SMA > slow-SMA, flat otherwise | fast ∈ {10, 20, 50}, slow ∈ {50, 100, 200}, fast<slow | Trend-following baseline |
| 2 | `rsi-mean-reversion` | S&P 500 (per-name, max 20 concurrent) | Long on RSI < lower, exit on RSI > upper | lookback ∈ {7,14,21}, lower ∈ {20,25,30}, upper ∈ {55,65,75} | Classic mean reversion |
| 3 | `cross-sectional-momentum` | S&P 500 | Monthly: long top-decile by 12-1 month return | lookback ∈ {6,9,12} mo, skip ∈ {0,1} mo, top-pct ∈ {5,10,20}% | Jegadeesh-Titman style |
| 4 | `pairs-trading` | 5 fixed pairs: KO/PEP, MA/V, GOOG/META, XOM/CVX, JPM/BAC | Long underperformer + short outperformer when spread z-score breaches threshold | lookback ∈ {30,60,90} d, entry-z ∈ {1.5,2,2.5}, exit-z ∈ {0,0.5} | **Market-neutral. Requires shorting.** Only strategy with `allow_short=True`. |
| 5 | `bollinger-breakout` | SPY | Long on close > upper band, flat on close < middle band | lookback ∈ {10,20,30}, std ∈ {1.5,2,2.5} | Volatility breakout |
| 6 | `buy-hold-spy` | SPY | Always long | (none) | Benchmark for everything else |

### 5.2 Dashboard-integrated (3)

| # | Slug | Universe | Signal | Sweep grid | Notes |
|---|---|---|---|---|---|
| 7 | `news-sentiment-momentum` | Top-100 S&P 500 names by news coverage (rolling) | Daily rank by weighted combination of (a) 7-day rolling news cluster volume and (b) cluster-level sentiment from Phase 3 News data. Long top decile, monthly rebalance. | sentiment-weight ∈ {0.3,0.5,0.7}, lookback ∈ {3,7,14} d, top-pct ∈ {5,10,20}% | Uses existing `news_*` tables. `inception_date` = Phase 3 News live date (short track record, flagged honestly on the tile). |
| 8 | `macro-regime-overlay` | Wrapper around `cross-sectional-momentum` | Define 4 macro regimes from FRED: `T10Y2Y` (yield-curve slope), `UNRATE` MoM Δ, and `INDPRO` YoY % (industrial production as the free ISM-PMI proxy). In "risk-off" regimes, halve gross exposure or rotate into defensives (XLP/XLU/XLV equal-weight). | regime thresholds (small grid), defensive-rotation ∈ {true,false} | Uses existing `econ_series` (FRED) data. Shown alongside vanilla momentum to make the value-add visible. |
| 9 | `multi-factor-combo` | S&P 500 | Composite score = z(12-1 momentum) + z(-1×P/B) + z(-σ) + z(ROE). Long top decile, monthly rebalance. | factor-weights grid (4 weights × 3 levels), top-pct ∈ {5,10}% | Fundamentals (P/B, ROE) from yfinance `Ticker.info` / `quarterly_financials`, cached. |

### 5.3 Frontend categorization

On `/quant` home the 9 strategies group into three bento sections: **Classics** (1–5), **Benchmark** (6), **Alpha** (7–9).

## 6. Data model (Supabase / SQLAlchemy)

New tables in `backend/app/models.py`. All use the existing `Base = declarative_base()` setup. Created automatically on first boot via `init_db()`.

```python
class BarCache(Base):
    __tablename__ = "bar_cache"
    symbol: str                    # PK part 1
    date: date                     # PK part 2 (US trading day)
    open, high, low, close, adj_close: Decimal
    volume: int
    source: str                    # "yfinance"
    fetched_at: datetime
    # indexes: (symbol, date) PK; (date) for universe-wide reads

class Strategy(Base):
    __tablename__ = "strategies"
    slug: str                      # PK
    name, category, methodology_blurb: str
    universe_kind: str             # "spy" | "sp500" | "pairs-fixed" | "news-top100"
    inception_date: date
    live_start_date: date          # in-sample / out-of-sample boundary
    chosen_params: JSON
    cost_model: JSON               # {commission, slippage_bps, allow_short}
    enabled: bool
    last_forward_step_date: date | None

class StrategyRun(Base):
    __tablename__ = "strategy_runs"
    id: int                        # PK
    strategy_slug: FK
    run_kind: str                  # "inception-walkforward" | "param-sweep"
    started_at, finished_at: datetime
    status: str                    # "pending" | "running" | "success" | "failed"
    progress: JSON                 # {windows_done, windows_total}
    error: str | None
    summary_metrics: JSON
    walkforward_windows: JSON
    param_sweep: JSON              # {(params): metrics} flattened for heatmap
    # idx: (strategy_slug, started_at desc)

class EquityPoint(Base):
    __tablename__ = "strategy_equity"
    strategy_slug: FK              # PK part 1
    date: date                     # PK part 2
    equity, cash: Decimal
    gross_exposure, net_exposure: Decimal
    daily_return: Decimal
    phase: str                     # "backtest" (pre-live_start) | "forward" (post)
    # idx: PK + (strategy_slug, date desc) for sparkline queries

class SimulatedTrade(Base):
    __tablename__ = "strategy_trades"
    id: int                        # PK
    strategy_slug: FK
    date: date
    symbol: str
    side: str                      # "buy" | "sell" | "short" | "cover"
    qty: int
    price: Decimal                 # close-price fill + slippage
    commission, notional: Decimal
    phase: str
    # idx: (strategy_slug, date desc)

class Position(Base):
    __tablename__ = "strategy_positions"
    strategy_slug: FK              # PK part 1
    symbol: str                    # PK part 2
    qty: int                       # +long / -short
    avg_cost: Decimal
    opened_at, last_marked_at: date
```

**Idempotency rules (load-bearing — get these wrong and the equity curve double-counts):**

- Forward-step is keyed `(strategy_slug, date)` on both `strategy_equity` and `strategy_trades`. Re-running the same trading day is a no-op (upsert with `ON CONFLICT DO NOTHING` semantics).
- A forward-step refuses to run if `last_forward_step_date >= target_date`. The job advances date strictly monotonically.
- The inception walk-forward writes equity rows with `phase="backtest"` for dates < `live_start_date` and is gated by **deleting prior backtest rows for that strategy before insert** (full rewrite of the backtest phase). Forward-step writes `phase="forward"` and never touches backtest rows.

**Storage estimate:**
- `bar_cache`: ~500 symbols × ~252 days/yr × ~11 yr ≈ 1.4M rows × ~100 B ≈ ~140 MB.
- `strategy_equity`: 9 × ~3,000 days ≈ 27k rows.
- `strategy_trades`: highly variable; bounded < 100k rows total in Q1.
- `strategy_runs`: ~9 rows × ~5 reruns ≈ ~45 rows; `param_sweep` JSON is the largest column (50–100 KB each).

## 7. API surface (`/api/quant/*`)

All auth-gated via the existing dependency.

- `GET /overview` — bento home: hero combined equity (sum of forward-phase equity across enabled strategies, normalized to $100k), leaderboard rows, recent-trades feed (latest 20), universe-health tile (bar-cache freshness, last forward-step timestamp per strategy).
- `GET /strategy/{slug}` — detail page: metadata + methodology blurb + chosen params + full equity series (each point tagged with `phase`) + drawdown series + monthly returns matrix + tear-sheet metrics + walk-forward window list + parameter-sweep grid + current positions + recent 100 trades.
- `GET /strategy/{slug}/trades?cursor=&limit=` — paginated trade history (cursor on `(date desc, id desc)`).
- `POST /strategy/{slug}/recompute-backtest` — trigger inception walk-forward as a background job. Returns `202` + `run_id`. Returns `409` if a run is already in flight for the strategy.
- `GET /runs/{run_id}` — poll status (`pending` | `running` | `success` | `failed`) + progress + summary metrics on completion.

Response shapes use Pydantic models alongside the existing patterns in `backend/app/models.py`.

## 8. Frontend (`/quant`)

Reuses: `BentoGrid`, `BentoTile`, `Panel` (with the `href` prop already in place for tile→detail linking), `Breadcrumb`, `LineChart`, `ChartControls`, `ReturnsTable`, ⌘K `CommandPalette`.

**New components:**
- `EquityCurvePanel` — LineChart wrapper with backtest/forward phase shading + optional SPY overlay
- `DrawdownPanel` — underwater chart
- `MonthlyReturnsHeatmap` — rows = year, cols = month
- `ParameterSweepHeatmap` — 2-axis grid (most sensitive two params), color = in-sample Sharpe, marker at `chosen_params`
- `WalkforwardWindowsTable` — train range / test range / chosen params / OOS Sharpe per row
- `StrategyTile` — sparkline + name + total return + Sharpe + live-since chip
- `LeaderboardPanel` — sortable by total return / Sharpe / DD
- `MethodologyPanel` — prose blurb (no code)

**`QuantRoute.tsx`** (bento home): Hero (combined equity + leaderboard), Classics section (5 tiles), Alpha section (3 tiles), Benchmark tile, Recent Trades feed, Universe Health tile.

**`StrategyRoute.tsx`** (drill-down): Header (name + chip + params + live-since + 4 headline metrics) → Equity panel → Drawdown panel → Monthly Returns heatmap → Parameter Sweep heatmap → Walk-forward Windows table → Tear-sheet Metrics panel → Current Positions table → Recent Trades table → Methodology blurb → "Recompute Backtest" button (fires POST, polls run status).

**Routes added** to `frontend/src/router.tsx`: `/quant`, `/quant/strategy/:slug`. ⌘K palette: "Quant Lab" + one entry per strategy.

## 9. Error handling

- **Strategy fails to compute on a given day** → structured log, mark latest `StrategyRun` failed, skip that strategy for the day (don't poison the others), retry tomorrow.
- **Missing bars (delisting, IPO, halts)** → strategy contract: if a held symbol has no bar on `date`, mark at last known close and keep the position; if the gap exceeds 5 days, liquidate at last known close on day 5.
- **yfinance garbage / rate-limit** → bar refresh retries with exponential backoff up to 3 attempts, then exits. Forward-step refuses to run if bars for `target_date` are missing for >5% of the universe (logged + alerted via existing structured logging).
- **Concurrent recompute** → `POST /recompute-backtest` returns `409` if a run with `status in ("pending", "running")` already exists for the strategy.
- **Fly machine restart mid-backtest** → on boot, any `StrategyRun` left with `status="running"` for >2 hours is marked `failed` with `error="interrupted"`. UI shows a Retry button.

## 10. Testing

TDD throughout, matches existing project pattern (every PR ships with tests).

**Backend:**
- Per strategy: `generate_signals` against canned bar fixtures (deterministic in / deterministic out).
- Engine: walk-forward window builder, OOS stitching, vectorbt grid wrapping, cost model arithmetic.
- Forward-step: idempotency under replay (running the same day twice produces identical state), monotonicity (refuses to go backwards), catch-up loop bounded.
- Routes: response shapes, auth gating, pagination cursor stability, `409` on concurrent recompute.
- Scheduler: `warm_bars` → `forward_step_all_strategies` ordering.

**Frontend:**
- Route rendering with fixture data.
- Tile data shapes; chart panels render with fixture data.
- "Recompute" button state machine (idle → triggered → polling → success/failed).
- Accessibility: prefers-reduced-motion respected (matches existing convention).

**Playwright E2E:** log in → navigate to `/quant` → see leaderboard → click a strategy tile → see detail page with equity + tear-sheet.

## 11. Performance + cost

- **Inception walk-forward (all 9 strategies × ~11 yr):** target <10 min on Fly shared-cpu-1x 1 GB. vectorbt's vectorization carries this. News-sentiment and multi-factor are the heaviest.
- **Daily forward-step (all 9 strategies):** target <60 s.
- **Page loads:** all API responses served from Supabase, no on-the-fly computation. `/overview` < 300 ms p95; detail page < 500 ms p95.
- **Cost:** **zero new $/mo in Q1.** yfinance is free, Supabase storage adds ~150 MB, Fly compute fits within existing capacity.

## 12. Security

- Same `DASHBOARD_TOKEN` gate as the rest of the dashboard.
- `recompute-backtest` rate-limited (one in-flight run per strategy via DB check, not in-memory).
- No new secrets in Q1.

## 13. Implementation plan decomposition (sketch — final split is the writing-plans skill's call)

Likely **4 plans**:
- **Q1a — Backend foundation:** models + migrations + `bar_cache` + `bars.py` + `Strategy` base + `engine.run_grid/run_single` + walk-forward window builder + cost model + first 2 strategies (`sma-crossover`, `buy-hold-spy`) as proof of pipeline.
- **Q1b — Remaining 7 strategies:** each strategy as its own task, including the 3 dashboard-integrated ones (which require `news_*` / `econ_series` read access).
- **Q1c — Forward-step runner + scheduler + API routes:** `runner.py`, `warm_bars` + `forward_step_all_strategies` APScheduler jobs, all `/api/quant/*` routes, background job machinery.
- **Q1d — Frontend bento + detail page + deploy:** all new components, `QuantRoute`, `StrategyRoute`, router wiring, ⌘K entries, Playwright E2E, Fly + Vercel deploy.

## 14. Out of scope / explicitly deferred

- Live Alpaca order submission (→ Q2)
- Intraday bars / streaming (→ Q3, Q4)
- Leverage, options, margin modeling
- Custom strategy authoring via UI
- Public share links

## 15. Open questions

None — all decisions resolved in brainstorm. Proceeding to writing-plans.
