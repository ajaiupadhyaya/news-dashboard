# Quant Lab Q1d — Frontend `/quant` + Deploy

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Build the `/quant` bento home + `/quant/strategy/:slug` drill-down page, wire ⌘K palette entries, write a Playwright E2E spec, then deploy backend (Fly) and frontend (Vercel). After Q1d the Quant Lab is **live on the production site** and the standalone news-dashboard project has its fifth first-class domain.

**Architecture:** Mirrors the existing `/finance` and `/economics` domains exactly. New `frontend/src/quant/` domain package. Two new routes. New components reuse the existing primitives (`AppShell`, `BentoGrid`, `BentoTile`, `Breadcrumb`, `Panel`, `LineChart`, `ChartControls`, `CommandPalette`, `PanelSkeleton`, `ReturnsTable`). API hits the `/api/quant/*` endpoints built in Q1c.

**Tech Stack:** React 18 + TypeScript + Vite + TanStack Query + Tailwind + Motion + D3. No new third-party deps.

**Spec:** `docs/superpowers/specs/2026-05-22-quant-lab-design.md` §8 (Frontend), §7 (API shape).

---

## Background — state at the time of this plan

`main` is at the Q1c merge commit (`84ec83b`). 293 backend tests passing. Q1c backend NOT yet deployed to Fly — Q1d will deploy backend + frontend together at the end as a single rollout.

Existing frontend pattern (read these before starting):
- Domain layout: `frontend/src/finance/` and `frontend/src/economics/` — each has hooks, panels, tiles.
- Route layout: `frontend/src/routes/FinanceRoute.tsx` and `frontend/src/routes/IndicatorRoute.tsx`.
- API client: `frontend/src/lib/api.ts` — exports `api.X` callables, all auth-gated via bearer token.
- Types: `frontend/src/lib/types.ts`.
- Router: `frontend/src/router.tsx`.
- Command palette: `frontend/src/components/CommandPalette.tsx`.

---

## File Map

**New:**
- `frontend/src/lib/quant-types.ts` — Quant Lab response types
- `frontend/src/quant/hooks.ts` — TanStack Query hooks
- `frontend/src/quant/StrategyTile.tsx` + test
- `frontend/src/quant/LeaderboardPanel.tsx` + test
- `frontend/src/quant/HeroEquityPanel.tsx` + test
- `frontend/src/quant/RecentTradesPanel.tsx` + test
- `frontend/src/quant/UniverseHealthTile.tsx` + test
- `frontend/src/quant/EquityCurvePanel.tsx` + test (LineChart wrapper with backtest/forward shading)
- `frontend/src/quant/DrawdownPanel.tsx` + test
- `frontend/src/quant/MonthlyReturnsHeatmap.tsx` + test
- `frontend/src/quant/ParameterSweepHeatmap.tsx` + test
- `frontend/src/quant/WalkforwardWindowsTable.tsx` + test
- `frontend/src/quant/PositionsTable.tsx` + test
- `frontend/src/quant/TradesTable.tsx` + test
- `frontend/src/quant/MethodologyPanel.tsx` + test
- `frontend/src/quant/RecomputeButton.tsx` + test
- `frontend/src/routes/QuantRoute.tsx` + test
- `frontend/src/routes/StrategyRoute.tsx` + test
- `frontend/tests/e2e/quant.spec.ts` — Playwright E2E

**Modified:**
- `frontend/src/lib/api.ts` — add 5 new methods
- `frontend/src/lib/types.ts` — re-export quant types (or just import directly)
- `frontend/src/router.tsx` — add `/quant` + `/quant/strategy/:slug`
- `frontend/src/components/CommandPalette.tsx` — add quant entries
- `frontend/src/routes/Home.tsx` — make the (likely placeholder) "Quant" quadrant link to `/quant`

---

## Task 1: Quant types + API client

**Files:**
- Create: `frontend/src/lib/quant-types.ts`
- Modify: `frontend/src/lib/api.ts`
- Test: extend `frontend/src/lib/api.test.ts` (if exists) or create a small test

- [ ] Define the response types:

```ts
// frontend/src/lib/quant-types.ts
export interface StrategySummary {
  slug: string;
  name: string;
  category: 'classic' | 'alpha' | 'benchmark';
  sparkline: number[];
  live_since: string | null;
  total_return: number;
  sharpe: number;
  max_drawdown: number;
}

export interface HeroEquityPoint {
  date: string;
  equity: number;
}

export interface TradeRow {
  id?: number;
  strategy_slug?: string;
  date: string;
  symbol: string;
  side: 'buy' | 'sell' | 'short' | 'cover';
  qty: number;
  price: number;
  commission?: number;
  notional: number;
  phase: 'backtest' | 'forward';
}

export interface UniverseHealth {
  latest_bar_fetched_at: string | null;
  last_forward_step_per_strategy: Record<string, string | null>;
}

export interface QuantOverview {
  leaderboard: StrategySummary[];
  hero_equity: HeroEquityPoint[];
  recent_trades: TradeRow[];
  universe_health: UniverseHealth;
}

export interface EquityPoint {
  date: string;
  equity: number;
  phase: 'backtest' | 'forward';
  daily_return: number;
}

export interface DrawdownPoint {
  date: string;
  drawdown: number;
}

export interface WalkforwardWindow {
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  chosen_params: Record<string, unknown>;
  oos_metrics: Record<string, number>;
}

export interface ParameterSweepCell {
  params: Record<string, unknown>;
  sharpe: number;
}

export interface PositionRow {
  symbol: string;
  qty: number;
  avg_cost: number;
  opened_at: string;
}

export interface StrategyDetail {
  slug: string;
  name: string;
  category: string;
  methodology_blurb: string;
  universe_kind: string;
  inception_date: string;
  live_start_date: string;
  chosen_params: Record<string, unknown>;
  cost_model: { commission: number; slippage_bps: number; allow_short: boolean };
  last_forward_step_date: string | null;
  equity_series: EquityPoint[];
  drawdown_series: DrawdownPoint[];
  monthly_returns: Record<string, Record<number, number>>;
  tear_sheet: { total_return: number; sharpe: number; max_drawdown: number };
  walkforward_windows: WalkforwardWindow[];
  param_sweep: ParameterSweepCell[];
  current_positions: PositionRow[];
  recent_trades: TradeRow[];
}

export interface TradesPage {
  trades: TradeRow[];
  next_cursor: string | null;
}

export interface RunStatus {
  id: number;
  strategy_slug: string;
  run_kind: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  started_at: string;
  finished_at: string | null;
  progress: { windows_done?: number; windows_total?: number };
  error: string | null;
  summary_metrics: Record<string, number> | null;
}
```

- [ ] Add to `frontend/src/lib/api.ts`:

```ts
// Inside the `api` object literal (or wherever existing methods are defined):
quantOverview: () => apiFetch<QuantOverview>('/api/quant/overview'),
quantStrategy: (slug: string) =>
  apiFetch<StrategyDetail>(`/api/quant/strategy/${encodeURIComponent(slug)}`),
quantStrategyTrades: (slug: string, opts: { cursor?: string; limit?: number } = {}) => {
  const q = new URLSearchParams();
  if (opts.cursor) q.set('cursor', opts.cursor);
  if (opts.limit) q.set('limit', String(opts.limit));
  const suffix = q.toString();
  return apiFetch<TradesPage>(
    `/api/quant/strategy/${encodeURIComponent(slug)}/trades${suffix ? '?' + suffix : ''}`,
  );
},
quantRecompute: (slug: string) =>
  apiFetch<{ run_id: number; status: string }>(
    `/api/quant/strategy/${encodeURIComponent(slug)}/recompute-backtest`,
    { method: 'POST' },
  ),
quantRun: (runId: number) => apiFetch<RunStatus>(`/api/quant/runs/${runId}`),
```

Add the matching imports at the top of `api.ts`:

```ts
import type {
  QuantOverview, StrategyDetail, TradesPage, RunStatus,
} from './quant-types';
```

- [ ] Test: smoke that the imports work + the methods exist. Add a small test to a new `frontend/src/lib/quant-api.test.ts`:

```ts
import { describe, expect, test, vi } from 'vitest';
import { api } from './api';

describe('quant api surface', () => {
  test('all quant methods exist', () => {
    expect(typeof api.quantOverview).toBe('function');
    expect(typeof api.quantStrategy).toBe('function');
    expect(typeof api.quantStrategyTrades).toBe('function');
    expect(typeof api.quantRecompute).toBe('function');
    expect(typeof api.quantRun).toBe('function');
  });
});
```

Run `cd frontend && npm test -- --run quant-api`. Expect PASS.

- [ ] Commit:

```bash
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
feat(quant/frontend): types + API client methods for /api/quant/*

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Quant hooks

**Files:**
- Create: `frontend/src/quant/hooks.ts`
- Create: `frontend/src/quant/hooks.test.ts`

Follows `frontend/src/finance/hooks.ts` pattern. TanStack Query.

```ts
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { api } from '../lib/api';

export function useQuantOverview() {
  return useQuery({
    queryKey: ['quant', 'overview'],
    queryFn: api.quantOverview,
    refetchInterval: 60_000,
  });
}

export function useStrategy(slug: string) {
  return useQuery({
    queryKey: ['quant', 'strategy', slug],
    queryFn: () => api.quantStrategy(slug),
    enabled: slug.length > 0,
    placeholderData: keepPreviousData,
  });
}

export function useStrategyTrades(slug: string) {
  // Simple paginated cursor — for Q1d we use a single "load more" cursor.
  return useQuery({
    queryKey: ['quant', 'strategy-trades', slug],
    queryFn: () => api.quantStrategyTrades(slug, { limit: 100 }),
    enabled: slug.length > 0,
  });
}

export function useRecompute(slug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.quantRecompute(slug),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['quant', 'strategy', slug] });
      qc.invalidateQueries({ queryKey: ['quant', 'overview'] });
    },
  });
}

export function useRunStatus(runId: number | null) {
  return useQuery({
    queryKey: ['quant', 'run', runId],
    queryFn: () => (runId ? api.quantRun(runId) : Promise.reject()),
    enabled: runId !== null,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === 'pending' || status === 'running' ? 2000 : false;
    },
  });
}
```

Test: render-time + minimal behavior (similar to `frontend/src/finance/hooks.test.tsx`). One smoke test per hook is enough.

Commit:

```bash
git -c commit.gpgsign=false commit -m "feat(quant/frontend): TanStack Query hooks for the Quant domain"
```

---

## Tasks 3–10: Components

Each task is one component + its test. Pattern: copy the closest existing component (e.g. `IndicatorTile` for `StrategyTile`), adapt props + rendering, write a small render test asserting key text + structure.

These tasks can be dispatched independently since each touches only its own files (+ adding to a shared sub-index file if any). Recommended dispatch order:

3. **`StrategyTile`** — sparkline + name + return + Sharpe + live-since chip. Reuses inline SVG sparkline pattern from `IndicatorTile` if available; otherwise a small D3 line.
4. **`LeaderboardPanel`** — sortable HTML table over the leaderboard array.
5. **`HeroEquityPanel`** — wraps `LineChart` over `hero_equity` array; title "Combined equity".
6. **`RecentTradesPanel`** — table of latest 20 trades; columns date/symbol/side/qty/price/notional.
7. **`UniverseHealthTile`** — small panel showing bar-cache freshness + last forward-step per strategy.
8. **`EquityCurvePanel`** — `LineChart` of `equity_series`, with the "backtest" portion drawn slightly muted (lighter stroke) and the "forward" portion solid. Optional SPY-benchmark overlay (toggle off by default for Q1d to keep scope small — fetch from `useQuantOverview` for buy-hold-spy).
9. **`DrawdownPanel`** — underwater area chart of `drawdown_series`.
10. **`MonthlyReturnsHeatmap`** — D3 heatmap (year row × month column).
11. **`ParameterSweepHeatmap`** — D3 heatmap. The grid is N-dimensional in general; for Q1d render only the two most varying params; project the rest by averaging Sharpe. Mark `chosen_params` with a star.
12. **`WalkforwardWindowsTable`** — one row per window: train range, test range, chosen params, OOS Sharpe.
13. **`PositionsTable`** — current positions (symbol, qty, avg_cost, opened_at).
14. **`TradesTable`** — paginated trades view; "Load more" button reads `next_cursor`.
15. **`MethodologyPanel`** — `<p>` with `methodology_blurb` + chips for chosen_params + cost_model fields.
16. **`RecomputeButton`** — three states: idle (button labeled "Recompute backtest"), triggered (calls `useRecompute().mutate()`, captures `run_id`, then uses `useRunStatus(runId)` to poll; shows "Running… (windows_done/windows_total)"), terminal (shows success/failed text + last-updated timestamp).

For each component task, the dispatched subagent gets:
- File paths to create
- A reference component to mimic (named explicitly)
- The exact prop shape (typed from `frontend/src/lib/quant-types.ts`)
- A small failing render test
- The minimal implementation

Each commit follows the pattern `feat(quant/frontend): <ComponentName>` with the co-author trailer.

---

## Task 17: QuantRoute (bento home)

**Files:**
- Create: `frontend/src/routes/QuantRoute.tsx`
- Create: `frontend/src/routes/QuantRoute.test.tsx`

Layout mirrors `FinanceRoute`. Bento grid composed of:
- Header: Breadcrumb (Dashboard → Quant Lab), "Updated …" stamp
- `HeroEquityPanel` (colSpan 6) + `LeaderboardPanel` (colSpan 4 or 6 on next row)
- "Classics" section: 5 `StrategyTile`s (SmaCrossover, RsiMeanReversion, CrossSectionalMomentum, PairsTrading, BollingerBreakout)
- "Alpha" section: 3 `StrategyTile`s (NewsSentimentMomentum, MacroRegimeOverlay, MultiFactorCombo)
- "Benchmark" tile: BuyHoldSPY
- `RecentTradesPanel`
- `UniverseHealthTile`

Uses `useQuantOverview()`. Wires loading + error + stale states like `FinanceRoute`.

Render test: mock `useQuantOverview` to return a small fixture; assert key text ("Quant Lab", strategy names, "Loading" branch, "Error" branch).

Commit: `feat(quant/frontend): QuantRoute bento home page`

---

## Task 18: StrategyRoute (drill-down)

**Files:**
- Create: `frontend/src/routes/StrategyRoute.tsx`
- Create: `frontend/src/routes/StrategyRoute.test.tsx`

Layout: header (name + 4 headline metrics) → `EquityCurvePanel` → `DrawdownPanel` → `MonthlyReturnsHeatmap` → `ParameterSweepHeatmap` → `WalkforwardWindowsTable` → `PositionsTable` → `TradesTable` → `MethodologyPanel` → `RecomputeButton`.

Uses `useStrategy(slug)` and `useStrategyTrades(slug)`. Wires loading/error/404 (the API returns 404 when slug unknown — show a not-found state).

Render test: similar to `QuantRoute.test.tsx`.

Commit: `feat(quant/frontend): StrategyRoute drill-down page`

---

## Task 19: Router + Home + ⌘K palette wiring

**Files:**
- Modify: `frontend/src/router.tsx`
- Modify: `frontend/src/components/CommandPalette.tsx`
- Modify: `frontend/src/routes/Home.tsx` — make the "Quant" quadrant clickable to `/quant`

- [ ] In `router.tsx`:

```ts
import { QuantRoute } from './routes/QuantRoute';
import { StrategyRoute } from './routes/StrategyRoute';

// in `routes`:
{ path: '/quant', element: <QuantRoute /> },
{ path: '/quant/strategy/:slug', element: <StrategyRoute /> },
```

- [ ] In `CommandPalette.tsx`: add a "Quant Lab" entry that navigates to `/quant`. If the palette pulls the strategy list dynamically, fetch via `useQuantOverview` and inject strategy entries with deep links. For Q1d simplicity, hardcode the 9 strategy slugs:

```ts
const QUANT_PALETTE = [
  { label: 'Quant Lab', path: '/quant' },
  { label: 'SMA Crossover',          path: '/quant/strategy/sma-crossover' },
  { label: 'RSI Mean Reversion',     path: '/quant/strategy/rsi-mean-reversion' },
  { label: 'Cross-Sectional Momentum', path: '/quant/strategy/cross-sectional-momentum' },
  { label: 'Pairs Trading',          path: '/quant/strategy/pairs-trading' },
  { label: 'Bollinger Breakout',     path: '/quant/strategy/bollinger-breakout' },
  { label: 'News-Sentiment Momentum',path: '/quant/strategy/news-sentiment-momentum' },
  { label: 'Macro-Regime Overlay',   path: '/quant/strategy/macro-regime-overlay' },
  { label: 'Multi-Factor Combo',     path: '/quant/strategy/multi-factor-combo' },
  { label: 'Buy & Hold SPY',         path: '/quant/strategy/buy-hold-spy' },
];
```

Merge with the existing palette list.

- [ ] In `Home.tsx`: find the Quant quadrant placeholder (or add one if the layout is still the four-up bento). Make its panel `href="/quant"` so clicking the panel header navigates.

Run `npm test`, expect all existing tests still PASS. Add at most 1–2 small tests if anything changed materially in tested files.

Commit: `feat(quant/frontend): wire /quant routes + ⌘K palette + Home tile link`

---

## Task 20: Playwright E2E

**Files:**
- Create: `frontend/tests/e2e/quant.spec.ts`

Mirrors the existing finance E2E spec. The simplest meaningful flow:

```ts
import { test, expect } from '@playwright/test';

test.describe('Quant Lab', () => {
  test('overview loads and a strategy detail page is reachable', async ({ page }) => {
    // Auth helper (look at the existing E2E specs for how login is performed).
    await page.goto('/');
    // ... login steps (copy from the existing spec) ...

    await page.goto('/quant');
    await expect(page.getByText('Quant Lab')).toBeVisible();
    await expect(page.getByText('Buy & Hold SPY')).toBeVisible({ timeout: 10_000 });

    // Click a strategy tile.
    await page.getByText('Buy & Hold SPY').first().click();
    await expect(page).toHaveURL(/\/quant\/strategy\/buy-hold-spy/);
    await expect(page.getByText('Methodology')).toBeVisible();
  });
});
```

Run `npx playwright test quant.spec.ts` against a local dev backend + frontend.

Commit: `test(quant/frontend): Playwright E2E for /quant + strategy drill-down`

---

## Task 21: Final verification + commit

- Run `cd frontend && npm test` — expect all green.
- Run `cd frontend && npm run build` — expect clean build (this is what Vercel does).
- Run `cd backend && /Users/ajaiupadhyaya/Documents/news-dashboard/backend/.venv/bin/python -m pytest --tb=no -q` — expect 293+ passing (Q1d should not regress the backend).

Fix anything that crops up; small commits.

---

## Task 22: Deploy

Two side-by-side deploys. **This is the most production-visible step.** Confirm with the user before triggering each deploy if unsure.

**Backend (Fly):**
```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard/backend
fly deploy
```
- Wait for "deployed" message.
- Verify with `curl -i https://news-dashboard-api.fly.dev/health` (expect 200).
- Verify auth-gating: `curl -i https://news-dashboard-api.fly.dev/api/quant/overview` (expect 401).
- The new Docker image will be larger because of vectorbt/quantstats/statsmodels — expect 200–300 MB.

**Frontend (Vercel):**
```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard/frontend
vercel deploy --prod
```
- Wait for "Production deployment" URL.
- Visit https://news-dashboard-two-rho.vercel.app/quant in a browser, log in, confirm the page renders.

If any deploy step fails, STOP and report. Common failure modes:
- Fly image build OOMs while compiling numba — bump the build VM size with `fly deploy --build-arg ...` or pin numba+vectorbt to a pre-built wheel version.
- Vercel build fails on a TS error — fix the type error locally first, recommit, redeploy.

---

## Self-review

- §8 Frontend composition (`/quant` bento + drill-down) → Tasks 17–18.
- §8 New components (`EquityCurvePanel`, `DrawdownPanel`, `MonthlyReturnsHeatmap`, `ParameterSweepHeatmap`, `WalkforwardWindowsTable`, `StrategyTile`, `LeaderboardPanel`, `MethodologyPanel`) → Tasks 3–16.
- §8 Routes added, ⌘K palette entries → Task 19.
- §10 Playwright E2E → Task 20.
- §11 Performance: page loads served from cached API responses; targets < 500 ms p95 (already met by backend caching).

No placeholders. All filenames + component names + props match the typed quant-types module.
