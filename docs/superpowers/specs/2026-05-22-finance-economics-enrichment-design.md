# Finance & Economics Enrichment — Design Spec

**Date:** 2026-05-22
**Status:** Approved design — ready for implementation planning
**Working directory:** `~/Documents/news-dashboard`
**Parent spec:** `docs/superpowers/specs/2026-05-20-news-dashboard-design.md` (§5 Layout, §6 Finance/Economics, §8 Design)

---

## 1. Purpose

The Finance and Economics domains are live but thin — each is a small 2×2 quadrant
panel plus a single per-item drill-down. This effort **fleshes them out** into rich,
interactive dashboards: it adds a new middle navigation tier (full **domain pages**),
expands data coverage, upgrades the chart system, and raises interactivity — without
disturbing the calm four-quadrant home.

It is purely additive and reuses the existing backend (FastAPI + yfinance + FRED)
and frontend (Vite/React/D3/Motion) architecture. No new data sources or paid APIs.

## 2. Goals & non-goals

**Goals**
- A new tier: a full-screen, bento-grid **domain page** for Finance and for Economics.
- Broaden Finance to **multi-asset** (equities, crypto, commodities, rates, FX) and
  add top movers + market internals.
- Broaden Economics to **~16–20 indicators**, grouped into macro categories.
- Upgrade the shared chart system: timeframe controls, chart-type toggle, technical
  overlays, RSI/MACD sub-charts, indicator comparison.
- Make the dead ⌘K "Search" button a working **command palette**.
- Raise interactivity throughout — sortable tables, hover detail, micro-interactions.

**Non-goals**
- No new or paid data sources — yfinance and FRED (both free) only.
- Not the AI layer (Phase 5) — drill-downs keep their reserved "why this matters" slot.
- Not the News or Politics domains.
- No change to the four-quadrant home's identity — only its panel headers gain links.
- No visual-theme overhaul — the existing dark design-token system stays; richness
  comes from density, motion, and bespoke charts.

## 3. Decisions made (2026-05-22 brainstorm)

| Decision | Choice |
|---|---|
| Where new features live | **Add domain pages** — a 3-tier structure: home glance → domain page → item drill-down. Resolves the parent spec §5's "click a panel opens a page" intent. |
| Finance scope | **Multi-asset** — equities, crypto, commodities, Treasury rates, FX. |
| Economics scope | **Expanded & categorized** — ~16–20 FRED indicators across 6 categories. |
| Domain-page layout | **Bento grid** — a packed grid of deliberately-sized tiles around a hero chart. |
| Visual theme | Unchanged dark design-token theme; richness via density + motion + charts. |

## 4. Architecture

A new **domain page** tier sits between the home and the item drill-downs.

**Routes (frontend, `router.tsx`):**
- `/finance` — the Finance domain page (new).
- `/economics` — the Economics domain page (new).
- `/finance/:symbol` — instrument drill-down (exists; enriched).
- `/economics/:seriesId` — indicator drill-down (exists; enriched).

**Navigation:** each home quadrant panel header becomes a link to its domain page
(via the existing shared-element View Transition). Domain pages and drill-downs show
a `← Dashboard / Finance` breadcrumb. The 2×2 home stays a calm glance — its panels
are unchanged summaries beyond the new header link.

**Shared building blocks (new):**
- `components/BentoGrid.tsx` — the bento layout primitive (CSS-grid with named,
  deliberately-sized tile slots; collapses to one column on small screens).
- `components/Breadcrumb.tsx` — the `← Dashboard / <Domain>` trail.
- `components/CommandPalette.tsx` — the ⌘K palette (see §7).

**Core principle unchanged:** the frontend never blocks on a third-party API.
Domain pages read pre-computed, TTL-cached endpoints; the scheduler keeps them warm.

## 5. Finance domain

### 5.1 Finance domain page (`/finance`)

A bento grid (`FinanceRoute.tsx`) of tiles:

- **Hero market chart** — a large interactive chart of a selected index (default
  S&P 500). Timeframe pills (1D / 1W / 1M / 6M / 1Y / 5Y) and a chart-type toggle
  (line / area / candles). The index name is a control to switch index.
- **Asset-class tiles** — Equities, Crypto, Commodities, Rates, FX. Each is a
  mini-card: a representative ticker's value, change, and sparkline. Representative
  tickers: Equities `^GSPC`, Crypto `BTC-USD`, Commodities `GC=F` (gold), Rates
  `^TNX` (10-yr yield), FX `DX-Y.NYB` (dollar index).
- **Indices grid** — S&P 500, Dow, Nasdaq, Russell 2000, VIX, each with value +
  change + sparkline.
- **Top movers** — the day's biggest gainers and losers (top 5 each) from a
  large-cap universe (the S&P 100 constituents; final list locked in the plan).
- **Sector heatmap** — the 11 SPDR sectors at full size (reuses `SectorHeatmap`).
- **Breadth & internals** — advance/decline, the A/D ratio, VIX level, and
  up/down counts across the movers universe (reuses/extends `BreadthGauge`).
- **Watchlist** — a full **sortable** table: symbol, price, change, % change,
  volume, sparkline; add/remove; row click → instrument drill-down (reuses and
  extends `WatchlistTable`).

### 5.2 Instrument drill-down (`/finance/:symbol`) — enriched

- **Price chart** upgraded: a timeframe selector (1D / 1W / 1M / 6M / 1Y / 5Y /
  MAX), a chart-type toggle (candles / line / area), and overlay toggles —
  SMA 20/50/200, **Bollinger Bands**, and **volume bars**.
- New **RSI** and **MACD** sub-charts rendered below the price chart.
- A **returns table** — 1W / 1M / 3M / 6M / YTD / 1Y / 3Y total return.
- Keeps: the momentum & risk stats, the fundamentals grid, the reserved AI slot.

### 5.3 Finance backend

- `routes/finance.py` — add `GET /api/finance/markets` (the domain-page payload:
  asset-class quotes, the rich indices list, `movers` = `{gainers, losers}`,
  sectors, breadth detail). The existing `/api/finance/overview` stays for the
  home panel.
- `GET /api/finance/instrument/{symbol}` — accept an optional `range` query param
  (`1d`/`1w`/`1mo`/`6mo`/`1y`/`5y`/`max`) mapped to a yfinance period/interval.
- `analysis/metrics.py` — add pure, TDD'd functions: `rsi`, `macd` (line, signal,
  histogram), `bollinger_bands` (upper, middle, lower), `period_returns`.
- `services/finance_service.py` — `build_markets()` assembles the domain payload;
  movers come from a batch yfinance fetch over the S&P 100 universe, sorted by
  daily % change. Per-symbol isolation — a failed ticker is skipped.
- `providers/yfinance_provider.py` — add a batch-history helper if needed for the
  movers universe; keep the single mockable `yf` seam.
- `scheduler.py` — add a `warm_markets` job (interval ~10 min).
- `models.py` — add `AssetClass`, `Mover`, `MarketsResponse`; extend `Technicals`
  with `rsi`, `macd_*`, `bollinger_*`, `volume`; add a `Returns` model.

## 6. Economics domain

### 6.1 Economics domain page (`/economics`)

A bento grid (`EconomicsRoute.tsx`) of tiles:

- **Macro hero chart** — a featured indicator (default CPI YoY), with a timeframe
  selector and a transform toggle (Level / YoY % / MoM %).
- **Indicator grid** — ~16–20 indicators grouped into six categories: **Growth,
  Inflation, Labor, Rates, Housing, Consumer**. Each indicator is a compact tile
  (value, change, trend marker, sparkline); the grouped grid doubles as an economy
  scorecard. Tile click → indicator drill-down.
- **Recession dashboard** — the yield-curve spread + Sahm rule + a composite
  recession-risk readout with a plain-language status.
- **Release calendar** — upcoming economic releases for the next ~2 weeks (reuses
  and extends `ReleaseCalendar`).

Indicator set (~18 series across the six categories — exact FRED IDs locked in the
plan; representative picks):
- **Growth** — Real GDP growth, Industrial Production, Retail Sales.
- **Inflation** — CPI, Core CPI, PCE price index.
- **Labor** — Unemployment Rate, Nonfarm Payrolls, Initial Jobless Claims,
  Labor-Force Participation.
- **Rates** — Fed Funds Rate, 10-Year Treasury, 2-Year Treasury, 10y–2y spread.
- **Housing** — Housing Starts, Building Permits, 30-Year Mortgage Rate.
- **Consumer** — Consumer Sentiment, Personal Saving Rate, Real Disposable Income.

### 6.2 Indicator drill-down (`/economics/:seriesId`) — enriched

- **Chart** gains a timeframe selector (1Y / 5Y / 10Y / MAX) and a **transform
  toggle** (Level / YoY % / MoM %) implemented via FRED's server-side `units`.
- **Compare** — overlay a second indicator on the chart, chosen from the indicator
  set; both series normalized for shared display.
- **Recession shading** — NBER recession periods shaded behind the series, derived
  from the FRED `USREC` series.
- Keeps: the summary stats, the recession-signal composite, the reserved AI slot.

### 6.3 Economics backend

- `services/economics_service.py` — expand `INDICATORS` to ~18 entries, each tagged
  with a category; add `build_dashboard()` (categories + all indicator summaries +
  the recession composite + the calendar).
- `routes/economics.py` — add `GET /api/economics/dashboard`; the existing
  `/api/economics/overview` stays for the home panel.
- `GET /api/economics/indicator/{series_id}` — accept optional `transform`
  (`lin`/`pc1`/`pch`) and `range` query params; include `recession_periods`
  (list of `{start, end}`) in the response.
- `providers/fred_provider.py` — add a helper to fetch `USREC` and derive
  contiguous recession intervals. Keep the single mockable `httpx` seam.
- `models.py` — add `IndicatorCategory`, `EconomicsDashboard`, `RecessionPeriod`;
  extend `IndicatorSummary` with `category`; extend `IndicatorDetail` with
  `recession_periods`.
- `scheduler.py` — the existing `warm_economics` job also warms the dashboard.

## 7. Cross-cutting

### 7.1 Command palette (⌘K)

`components/CommandPalette.tsx` — opened by ⌘K (or clicking the AppBar Search
button), it is a single overlay that searches and jumps to: any watchlist symbol
or typed ticker (→ instrument drill-down), any economic indicator (→ indicator
drill-down), and the domain pages / home. Keyboard-navigable; honors
`prefers-reduced-motion`. `AppBar.tsx` is wired to open it.

### 7.2 Chart-system upgrades

Shared additions under `charts/`, reused by both domains:
- `charts/TimeframeControl.tsx` — the segmented timeframe pill control.
- `charts/ChartTypeToggle.tsx` — line / area / candles toggle.
- `charts/RSIChart.tsx` and `charts/MACDChart.tsx` — bespoke technical sub-charts.
- `CandlestickChart`/`LineChart` extended with overlay support (Bollinger Bands,
  volume bars) and an optional comparison series.

Every chart keeps the existing chart-design-system conventions (`ChartFrame`,
`Axis`, `useChartDimensions`, design tokens, smooth enter/update transitions,
interactive crosshairs) and honors `prefers-reduced-motion`.

### 7.3 Design

The dark design-token theme is unchanged. Richness is expressed through bento
density, bespoke charts, spring micro-interactions, pervasive hover/focus states,
and sortable/expandable tables — per the parent spec §8 design bar (calm surface,
rich depth).

## 8. Data sources

All free, both already integrated:
- **yfinance** — equities, indices, crypto (`BTC-USD`), commodities (`GC=F`,
  `CL=F`), rates (`^TNX`, `^TYX`), FX (`DX-Y.NYB`, `EURUSD=X`), and the S&P 100
  movers universe.
- **FRED** — the ~18 economic indicators, plus `USREC` for recession periods.

## 9. Error handling

Per the parent spec §11. Per-provider isolation is preserved: a failed ticker or
series is skipped and logged, never blanking a tile or panel. Endpoints return
empty-but-valid payloads on total failure; panels show a subtle "stale" badge via
the existing TanStack Query `isStale` path. Scheduler jobs log and continue.

## 10. Testing

- **Backend (pytest):** the new analysis functions (`rsi`, `macd`,
  `bollinger_bands`, `period_returns`, recession-interval derivation) are pure and
  unit-tested TDD-first; provider helpers tested against mocked responses; the new
  routes tested with the cache and auth dependency.
- **Frontend (Vitest + Testing Library):** component tests for `BentoGrid`, the
  domain pages, the new chart controls and sub-charts, the command palette, and the
  enriched drill-downs; Playwright specs for home → domain page → item drill-down.

## 11. Scope & phasing

This is a large, additive effort. It is implemented as **two implementation plans**:

1. **Finance enrichment** — includes the shared foundations (`BentoGrid`,
   `Breadcrumb`, `CommandPalette`, the chart-system upgrades) since Finance needs
   them first, plus the Finance domain page, the enriched instrument drill-down,
   and the Finance backend.
2. **Economics enrichment** — the Economics domain page, the enriched indicator
   drill-down, and the Economics backend; reuses the shared foundations from Plan 1.

Each plan produces working, shippable software on its own. Out of scope: the AI
layer (Phase 5), News (Phase 3), Politics (Phase 4), and any paid data source.
