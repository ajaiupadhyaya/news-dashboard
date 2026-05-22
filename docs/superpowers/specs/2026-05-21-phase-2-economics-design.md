# News & Markets Dashboard — Phase 2 (Economics) Design Spec

**Date:** 2026-05-21
**Status:** Approved design — ready for implementation planning
**Working directory:** `~/Documents/news-dashboard`
**Parent spec:** `docs/superpowers/specs/2026-05-20-news-dashboard-design.md` (§6 Economics)

---

## 1. Purpose

Phase 2 adds the **Economics domain** end-to-end: a live Economics overview panel
on the four-quadrant Home (replacing the current "coming soon" placeholder) and
an indicator drill-down page. It is FRED-backed and mirrors the architecture of
the already-shipped, already-live Finance domain. Phase 1 (foundation + Finance)
is complete and deployed; Phase 2 is purely additive.

## 2. Goals & non-goals

**Goals**
- A live Economics overview panel: key macro-indicator tiles + an economic-release calendar.
- An indicator drill-down page: full time series, recession-signal composite, momentum/trend composite.
- Reuse the existing chart, motion, and design systems; add one new chart type (time-series line/area).
- Stay within the project's data budget — use only the free FRED API.
- The frontend never blocks on FRED — everything is pre-computed and cached (parent spec's core principle).

**Non-goals**
- No analyst-consensus / "expected" forecast data — free sources are unreliable. Surprise framing is **trend-relative**, not actual-vs-expected.
- No separate BLS or BEA integration — FRED mirrors the needed series.
- Not the AI "why this matters" layer — that is Phase 5 (a reserved placeholder slot only).

## 3. Decisions made (2026-05-21 brainstorm)

| Decision | Choice |
|---|---|
| "Surprise markers" | **Trend-relative** — latest vs. prior release + position within the recent range. No paid expectations data. |
| Data source | **FRED API only** (free, one key). FRED mirrors the BLS/BEA series needed. |
| Economic-release calendar | FRED's own release-dates endpoint — resolves the parent spec §13 deferred decision. |
| Phasing | One spec, one implementation plan — Phase 2 is additive; the foundation already exists. |
| Drill-down "economic-surprise index" | Reframed as a **momentum/trend composite** (no expectations data available). |

## 4. Architecture

Mirrors the Finance domain. Core principle unchanged: the frontend reads only
pre-computed, cached data; the scheduler refreshes it in the background.

**Data flow:** scheduler → `fred_provider` fetches series + release dates →
`econ_metrics` computes → `economics_service` assembles → stored in Postgres
(`econ_series`) + TTL cache → `/api/economics/*` serves cached → frontend renders.

### 4.1 Backend (`backend/app/`)

- `config.py` — add `FRED_API_KEY` (env var; blank in dev/tests).
- `providers/fred_provider.py` — FRED HTTP adapter (httpx). `get_series(series_id)`
  returns observations; `get_release_calendar()` returns recent/upcoming releases.
  One mockable seam; returns `[]` on any failure (graceful, like `yfinance_provider`).
- `analysis/econ_metrics.py` — pure, unit-tested functions: period-over-period
  change; year-over-year change; the **trend-relative marker** (the latest
  reading's position within its trailing range — a window scaled to the series
  frequency — bucketed to below-/in-/above-normal); per-indicator momentum; the
  recession-signal composite.
- `services/economics_service.py` — `build_overview()`, `build_indicator(series_id)`.
- `models.py` — add `IndicatorPoint`, `ReleaseEvent`, `IndicatorSummary`,
  `EconomicsOverview`, `IndicatorDetail`.
- `database.py` — add an `econ_series` table (`series_id`, `date`, `value`) for
  durable time-series caching, mirroring the `ohlcv` table.
- `routes/economics.py` — `GET /api/economics/overview` and
  `GET /api/economics/indicator/{series_id}`; auth-gated; served via the TTL cache.
- `scheduler.py` — add a `warm_economics` job (interval ~6h — econ data updates slowly).
- `main.py` — register the economics router.

### 4.2 Frontend (`frontend/src/`)

- `charts/LineChart.tsx` — a new bespoke time-series area/line chart for the chart
  system (crosshair, tooltip, smooth enter/update transitions; honors
  `prefers-reduced-motion`). Joins the existing `Sparkline` + `CandlestickChart`.
- `economics/EconomicsPanel.tsx` — the overview panel: indicator-tile grid + release calendar.
- `economics/IndicatorTile.tsx` — one tile: latest value, change vs. prior, trend-relative marker, sparkline.
- `economics/ReleaseCalendar.tsx` — upcoming/recent FRED releases.
- `economics/hooks.ts` — TanStack Query hooks for the two endpoints.
- `economics/RecessionSignals.tsx` + drill-down stat pieces.
- `routes/IndicatorRoute.tsx` — the drill-down page: full series via `LineChart`,
  recession-signal composite, momentum composite, and an empty slot reserved for
  the Phase 5 AI "why this matters" explainer.
- `lib/types.ts` + `lib/api.ts` — add Economics types and endpoint functions.
- `router.tsx` — add the `/economics/:seriesId` route.
- `routes/Home.tsx` — replace the Economics `ComingSoonPanel` with `EconomicsPanel`.
- The overview tile → drill-down uses the same shared-element View Transition the
  Finance domain already uses.

## 5. Data source — FRED

Base URL `https://api.stlouisfed.org/fred/`, `file_type=json`, `api_key` from
`FRED_API_KEY`.

- Series observations: `series/observations?series_id=<id>`.
- Release calendar: `releases/dates` (recent + upcoming release dates with release names).

**Indicator set (overview tiles):**

| Tile | FRED series | Headline value |
|---|---|---|
| Inflation (CPI) | `CPIAUCSL` | year-over-year % change of the index |
| Unemployment | `UNRATE` | latest rate (%) |
| Payrolls | `PAYEMS` | latest monthly change (jobs added, thousands) |
| Real GDP | `A191RL1Q225SBEA` | latest quarter, annualized % |
| Fed funds rate | `FEDFUNDS` | latest rate (%) |
| 10-yr Treasury | `DGS10` | latest yield (%) |

**Recession-signal series (drill-down composite):** `T10Y2Y` (10yr–2yr spread;
inversion signals risk) and `SAHMREALTIME` (Sahm-rule recession indicator).

## 6. The overview panel

Replaces the placeholder in the Economics quadrant: a grid of ~6 indicator tiles
plus the release calendar. Each tile shows the indicator name, the latest value
(formatted to its unit), the change vs. the prior release with up/down treatment,
a trend-relative marker (below-/in-/above-normal vs. the trailing range), and a
sparkline of recent history. Clicking a tile opens the drill-down via the
shared-element transition. Calm at rest; richness on hover and interaction, per
the parent spec's design bar.

## 7. The drill-down page (`/economics/:seriesId`)

A full indicator view: the complete time series rendered with `LineChart`
(interactive crosshair + tooltip); summary stats (latest, period change, YoY,
trailing range); the **recession-signal composite** (yield-curve spread + Sahm
indicator with a plain-language status); the **momentum/trend composite**; and an
empty slot reserved for the Phase 5 AI "why this matters" explainer.

## 8. Error handling

Per the parent spec §11. FRED unreachable, or a single series fails → serve
last-good cached data; the panel shows a subtle "stale" badge rather than
breaking. Per-indicator isolation — one failed series never blanks the panel.
Scheduler jobs log and continue. With `FRED_API_KEY` unset (local dev without a
key), the endpoints return an empty-but-valid payload so the UI degrades
gracefully.

## 9. Testing

- **Backend (pytest):** `fred_provider` tested against recorded/mocked FRED JSON;
  `econ_metrics` pure functions unit-tested (TDD); routes tested with the cache
  and auth dependency.
- **Frontend:** component tests for `EconomicsPanel`, `IndicatorTile`,
  `ReleaseCalendar`, `LineChart`, and the drill-down page; a Playwright spec for
  the economics overview → drill-down flow (API stubbed).

## 10. Scope

One implementation plan, roughly 16–20 TDD tasks, executed via subagent-driven
development. Out of scope: AI explainers (Phase 5), the News and Politics
domains, and any paid data source.
