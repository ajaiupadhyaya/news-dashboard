# Finance Enrichment — `/finance` Domain Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full-screen bento-grid Finance domain page at `/finance` — a hero market chart, asset-class tiles, an indices grid, top movers, a sector heatmap, market internals, and a sortable watchlist — plus the shared `BentoGrid` and `Breadcrumb` foundations.

**Architecture:** This is the third tier of the dashboard (home glance → domain page → item drill-down). It is **frontend-only**: the backend `/api/finance/markets` endpoint and the `MarketsResponse` shape already exist and are merged. The page reads the pre-computed, TTL-cached markets payload via a new `useMarkets` hook, lays tiles out in a new 6-column `BentoGrid` primitive, and reuses the existing chart system (`PriceChart`, `ChartControls`), `SectorHeatmap`, and `BreadthGauge`. Each home quadrant panel header gains a link to its domain page.

**Tech Stack:** Vite + React 19 + TypeScript, Tailwind v4 (`@theme` design tokens), Motion, D3, TanStack Query v5, React Router 7, Vitest + Testing Library, Playwright.

**Working directory:** `~/Documents/news-dashboard` — all paths below are relative to it. Frontend commands run from `frontend/`.

**Conventions for every task:**
- Tests run from `frontend/`: `npx vitest run <path>` for one file, `npx vitest run` for all.
- Type-check: `cd frontend && npx tsc --noEmit`. Build: `npm run build`.
- Commit after each task. Branch is created by the execution skill — do not work on `main`.
- Follow the existing component style: design-token Tailwind classes (`text-ink`, `bg-surface`, `border-border`, `text-up`, `text-down`, `text-accent`, …), `font-mono` for numbers/labels, `tabular-nums` for figures, `clsx` for conditional classes, Motion `spring` presets from `design/motion.ts`.

---

## File structure

**Created:**
- `frontend/src/components/BentoGrid.tsx` — the bento layout primitive (`BentoGrid` + `BentoTile`).
- `frontend/src/components/Breadcrumb.tsx` — the `← Dashboard / Finance` trail.
- `frontend/src/finance/AssetClassStrip.tsx` — the five asset-class mini-cards.
- `frontend/src/finance/IndicesGrid.tsx` — the major-indices list, each linking to its drill-down.
- `frontend/src/finance/TopMovers.tsx` — the day's biggest gainers and losers.
- `frontend/src/finance/BreadthInternals.tsx` — the breadth gauge plus the VIX level.
- `frontend/src/finance/MarketChart.tsx` — the hero market chart (selectable index, timeframe, chart type).
- `frontend/src/finance/MarketsWatchlist.tsx` — the full sortable watchlist table.
- `frontend/src/routes/FinanceRoute.tsx` — the `/finance` page that assembles the bento grid.
- Test files alongside each (`*.test.tsx`).
- `frontend/e2e/finance-domain.spec.ts` — the Playwright spec for home → `/finance` → drill-down.

**Modified:**
- `frontend/src/lib/format.ts` — add `formatValue` (plain non-currency number formatter).
- `frontend/src/lib/types.ts` — add `AssetClass`, `Mover`, `MarketsResponse`.
- `frontend/src/lib/api.ts` — add `api.markets`.
- `frontend/src/finance/hooks.ts` — add `useMarkets`.
- `frontend/src/components/Panel.tsx` — add an optional `href` prop that turns the panel title into a link.
- `frontend/src/finance/FinancePanel.tsx` — pass `href="/finance"` to its `Panel`.
- `frontend/src/components/Breadcrumb.tsx` consumer: `frontend/src/routes/InstrumentRoute.tsx` — replace its `← Dashboard` link with `<Breadcrumb>`.
- `frontend/src/router.tsx` — register the `/finance` route.
- `frontend/src/components/CommandPalette.tsx` — add a `/finance` destination.
- Test files touched by the above (`format.test.ts`, `finance/hooks.test.tsx`).

---

## Task 1: Markets data layer — `formatValue`, types, API, `useMarkets`

The shared plumbing every later task needs: a non-currency number formatter, the TypeScript mirrors of the backend markets shapes, the API function, and the query hook.

**Files:**
- Modify: `frontend/src/lib/format.ts`
- Modify: `frontend/src/lib/format.test.ts`
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/finance/hooks.ts`
- Modify: `frontend/src/finance/hooks.test.tsx`

- [ ] **Step 1: Write the failing `formatValue` test**

Append to `frontend/src/lib/format.test.ts`:

```ts
test('formatValue renders a plain separated number, two decimals', () => {
  expect(formatValue(5400)).toBe('5,400.00');
  expect(formatValue(4.3)).toBe('4.30');
  expect(formatValue(-0.5)).toBe('-0.50');
});
```

If `formatValue` is not already imported at the top of the file, add it to the existing import from `'./format'`.

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/lib/format.test.ts`
Expected: FAIL — `formatValue is not a function` / not exported.

- [ ] **Step 3: Implement `formatValue`**

Append to `frontend/src/lib/format.ts`:

```ts
/** "5,400.00" — a plain number with thousands separators and two decimals.
 *  For index levels, yields, and other non-currency values where the "$" of
 *  `formatPrice` would be wrong. */
export function formatValue(n: number): string {
  return n.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
```

- [ ] **Step 4: Add the markets types**

Append to `frontend/src/lib/types.ts` (after the existing `OverviewResponse` / finance block — placement is not critical):

```ts
/** Finance domain page (markets) — mirrors the backend markets models. */

export interface AssetClass {
  label: string;        // "Equities" | "Crypto" | "Commodities" | "Rates" | "FX"
  symbol: string;
  price: number;
  change_pct: number;
  sparkline: number[];
}

export interface Mover {
  symbol: string;
  price: number;
  change_pct: number;
}

export interface MarketsResponse {
  asset_classes: AssetClass[];
  indices: WatchlistQuote[];
  gainers: Mover[];
  losers: Mover[];
  sectors: SectorChange[];
  breadth: Breadth;
  updated_at: string;
}
```

- [ ] **Step 5: Add the API function**

In `frontend/src/lib/api.ts`, add `MarketsResponse` to the type import block:

```ts
import type {
  EconomicsOverview,
  IndicatorDetail,
  InstrumentResponse,
  MarketsResponse,
  OverviewResponse,
} from './types';
```

Then add this entry to the `api` object, right after `overview`:

```ts
  markets: () => apiFetch<MarketsResponse>('/api/finance/markets'),
```

- [ ] **Step 6: Write the failing `useMarkets` test**

In `frontend/src/finance/hooks.test.tsx`, replace the whole `vi.mock('../lib/api', …)` block with this (it adds `markets` to the mock):

```ts
vi.mock('../lib/api', () => ({
  api: {
    overview: vi.fn().mockResolvedValue({
      watchlist: [], indices: [], sectors: [],
      breadth: { advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0 },
      updated_at: '2026-05-20T20:00:00+00:00',
    }),
    instrument: vi.fn().mockResolvedValue({ symbol: 'AAPL' }),
    markets: vi.fn().mockResolvedValue({
      asset_classes: [], indices: [], gainers: [], losers: [], sectors: [],
      breadth: { advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0 },
      updated_at: '2026-05-21T20:00:00+00:00',
    }),
  },
}));
```

Update the import line to include `useMarkets`:

```ts
import { useOverview, useInstrument, useMarkets } from './hooks';
```

Append this test:

```ts
test('useMarkets fetches the finance markets payload', async () => {
  const { result } = renderHook(() => useMarkets(), { wrapper: QueryWrapper });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.updated_at).toBe('2026-05-21T20:00:00+00:00');
});
```

- [ ] **Step 7: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/finance/hooks.test.tsx`
Expected: FAIL — `useMarkets` is not exported.

- [ ] **Step 8: Implement `useMarkets`**

Append to `frontend/src/finance/hooks.ts`:

```ts
/** The Finance domain-page markets payload — refetched every 60s. */
export function useMarkets() {
  return useQuery({
    queryKey: ['markets'],
    queryFn: api.markets,
    refetchInterval: 60_000,
  });
}
```

- [ ] **Step 9: Run all touched tests + type-check**

Run: `cd frontend && npx vitest run src/lib/format.test.ts src/finance/hooks.test.tsx && npx tsc --noEmit`
Expected: PASS, no type errors.

- [ ] **Step 10: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/lib/format.ts frontend/src/lib/format.test.ts \
  frontend/src/lib/types.ts frontend/src/lib/api.ts \
  frontend/src/finance/hooks.ts frontend/src/finance/hooks.test.tsx
git commit -m "feat(finance): add markets data layer — formatValue, types, useMarkets"
```

---

## Task 2: `BentoGrid` + `BentoTile` layout primitive

A 6-column CSS-grid that collapses to one column on small screens, plus a tile component with a deliberate column span and an optional uppercase section header.

**Files:**
- Create: `frontend/src/components/BentoGrid.tsx`
- Create: `frontend/src/components/BentoGrid.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/BentoGrid.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { BentoGrid, BentoTile } from './BentoGrid';

test('renders tiles with their titles and content', () => {
  render(
    <BentoGrid>
      <BentoTile title="Indices" colSpan={2}>
        <p>tile body</p>
      </BentoTile>
      <BentoTile colSpan={4}>
        <p>untitled body</p>
      </BentoTile>
    </BentoGrid>,
  );
  expect(screen.getByRole('heading', { name: 'Indices' })).toBeInTheDocument();
  expect(screen.getByText('tile body')).toBeInTheDocument();
  expect(screen.getByText('untitled body')).toBeInTheDocument();
});

test('applies the column-span class for the requested span', () => {
  const { container } = render(
    <BentoGrid>
      <BentoTile colSpan={4}>
        <p>wide</p>
      </BentoTile>
    </BentoGrid>,
  );
  expect(container.querySelector('.lg\\:col-span-4')).not.toBeNull();
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/components/BentoGrid.test.tsx`
Expected: FAIL — cannot resolve `./BentoGrid`.

- [ ] **Step 3: Implement `BentoGrid`**

Create `frontend/src/components/BentoGrid.tsx`:

```tsx
import type { ReactNode } from 'react';
import { motion } from 'motion/react';
import { clsx } from 'clsx';
import { fadeRise, spring } from '../design/motion';

/** The bento layout: a 6-column grid on large screens, one column below. */
export function BentoGrid({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-6">{children}</div>
  );
}

// Literal class strings so Tailwind's source scan picks every span up.
const COL_SPAN: Record<number, string> = {
  1: 'lg:col-span-1',
  2: 'lg:col-span-2',
  3: 'lg:col-span-3',
  4: 'lg:col-span-4',
  5: 'lg:col-span-5',
  6: 'lg:col-span-6',
};

interface BentoTileProps {
  /** Optional uppercase section header. Omit when the child renders its own. */
  title?: string;
  /** Columns to span on large screens (1–6). Full width below `lg`. */
  colSpan?: 1 | 2 | 3 | 4 | 5 | 6;
  children: ReactNode;
  className?: string;
}

/** One tile in the bento grid — a bordered surface card that enters with a
 *  soft rise, with an optional uppercase section header. */
export function BentoTile({
  title, colSpan = 2, children, className,
}: BentoTileProps) {
  return (
    <motion.section
      initial={fadeRise.initial}
      animate={fadeRise.animate}
      transition={spring.gentle}
      className={clsx(
        'flex flex-col overflow-hidden rounded-lg border border-border',
        'bg-surface p-4',
        COL_SPAN[colSpan],
        className,
      )}
    >
      {title && (
        <h2 className="mb-3 font-mono text-[10px] tracking-widest text-ink-mute
                       uppercase">
          {title}
        </h2>
      )}
      <div className="flex-1">{children}</div>
    </motion.section>
  );
}
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd frontend && npx vitest run src/components/BentoGrid.test.tsx`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/components/BentoGrid.tsx frontend/src/components/BentoGrid.test.tsx
git commit -m "feat(finance): add BentoGrid layout primitive"
```

---

## Task 3: `Breadcrumb` component + wire into `InstrumentRoute`

The `← Dashboard / Finance / AAPL` trail shown on domain pages and drill-downs. The first crumb is prefixed with `←`; the last crumb is the current page and is not a link.

**Files:**
- Create: `frontend/src/components/Breadcrumb.tsx`
- Create: `frontend/src/components/Breadcrumb.test.tsx`
- Modify: `frontend/src/routes/InstrumentRoute.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/Breadcrumb.test.tsx`:

```tsx
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { Breadcrumb } from './Breadcrumb';

test('renders linked crumbs and a plain final crumb', () => {
  renderWithProviders(
    <Breadcrumb
      trail={[
        { label: 'Dashboard', to: '/' },
        { label: 'Finance', to: '/finance' },
        { label: 'AAPL' },
      ]}
    />,
  );
  // First crumb is prefixed with the back arrow.
  expect(screen.getByRole('link', { name: '← Dashboard' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Finance' })).toBeInTheDocument();
  // The final crumb is the current page — text, not a link.
  expect(screen.queryByRole('link', { name: 'AAPL' })).toBeNull();
  expect(screen.getByText('AAPL')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/components/Breadcrumb.test.tsx`
Expected: FAIL — cannot resolve `./Breadcrumb`.

- [ ] **Step 3: Implement `Breadcrumb`**

Create `frontend/src/components/Breadcrumb.tsx`:

```tsx
import { Fragment } from 'react';
import { Link } from 'react-router-dom';

export interface Crumb {
  label: string;
  /** Destination. Omit for the current (final) page. */
  to?: string;
}

/** The "← Dashboard / Finance / AAPL" trail. The first crumb carries a back
 *  arrow; the final crumb is rendered as plain text (the current page). */
export function Breadcrumb({ trail }: { trail: Crumb[] }) {
  return (
    <nav
      aria-label="Breadcrumb"
      className="flex flex-wrap items-center gap-1.5 font-mono text-xs
                 text-ink-mute"
    >
      {trail.map((crumb, i) => {
        const last = i === trail.length - 1;
        const text = i === 0 ? `← ${crumb.label}` : crumb.label;
        return (
          <Fragment key={crumb.label}>
            {i > 0 && <span aria-hidden="true">/</span>}
            {crumb.to && !last ? (
              <Link
                to={crumb.to}
                viewTransition
                className="text-ink-soft transition-colors hover:text-accent"
              >
                {text}
              </Link>
            ) : (
              <span className={last ? 'text-ink' : undefined}>{text}</span>
            )}
          </Fragment>
        );
      })}
    </nav>
  );
}
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd frontend && npx vitest run src/components/Breadcrumb.test.tsx`
Expected: PASS.

- [ ] **Step 5: Wire `Breadcrumb` into `InstrumentRoute`**

In `frontend/src/routes/InstrumentRoute.tsx`, add the import (next to the other component imports):

```tsx
import { Breadcrumb } from '../components/Breadcrumb';
```

Then replace this block:

```tsx
        <Link
          to="/"
          viewTransition
          className="font-mono text-xs text-ink-soft transition-colors
                     hover:text-accent"
        >
          ← Dashboard
        </Link>
```

with:

```tsx
        <Breadcrumb
          trail={[
            { label: 'Dashboard', to: '/' },
            { label: 'Finance', to: '/finance' },
            { label: upper },
          ]}
        />
```

`Link` is still used elsewhere in the file (it is imported alongside `useParams`) — leave the import line as-is.

- [ ] **Step 6: Run the InstrumentRoute tests to confirm nothing broke**

Run: `cd frontend && npx vitest run src/routes/InstrumentRoute.test.tsx src/components/Breadcrumb.test.tsx && npx tsc --noEmit`
Expected: PASS, no type errors.

- [ ] **Step 7: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/components/Breadcrumb.tsx \
  frontend/src/components/Breadcrumb.test.tsx \
  frontend/src/routes/InstrumentRoute.tsx
git commit -m "feat(finance): add Breadcrumb, use it in the instrument drill-down"
```

---

## Task 4: `Panel` href prop + link the Finance home panel to `/finance`

The home quadrant panels stay calm summaries, but each header title becomes a link to its domain page. This task adds the capability to the shared `Panel` and wires the Finance panel.

**Files:**
- Modify: `frontend/src/components/Panel.tsx`
- Create: `frontend/src/components/Panel.test.tsx`
- Modify: `frontend/src/finance/FinancePanel.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/Panel.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { Panel } from './Panel';

test('renders a plain title when no href is given', () => {
  render(
    <Panel title="Finance" icon="💹">
      <p>body</p>
    </Panel>,
  );
  expect(screen.getByRole('heading', { name: 'Finance' })).toBeInTheDocument();
  expect(screen.queryByRole('link')).toBeNull();
});

test('renders the title as a link when href is given', () => {
  renderWithProviders(
    <Panel title="Finance" icon="💹" href="/finance">
      <p>body</p>
    </Panel>,
  );
  const link = screen.getByRole('link', { name: 'Open Finance' });
  expect(link).toHaveAttribute('href', '/finance');
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/components/Panel.test.tsx`
Expected: FAIL — no link is rendered (no `href` support yet).

- [ ] **Step 3: Implement the `href` prop**

Replace the entire contents of `frontend/src/components/Panel.tsx` with:

```tsx
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import { clsx } from 'clsx';
import { fadeRise, spring } from '../design/motion';

interface PanelProps {
  title: string;
  icon: string;
  /** When set, the panel title becomes a link to this domain page. */
  href?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** The shared frame for every domain panel — header bar plus body. When
 *  `href` is set the title links to the domain page. */
export function Panel({
  title, icon, href, action, children, className,
}: PanelProps) {
  const heading = (
    <h2
      className={clsx(
        'font-mono text-xs tracking-widest uppercase transition-colors',
        href ? 'text-ink-soft hover:text-accent' : 'text-ink-soft',
      )}
    >
      {title}
    </h2>
  );

  return (
    <motion.section
      initial={fadeRise.initial}
      animate={fadeRise.animate}
      transition={spring.gentle}
      className={clsx(
        'flex flex-col overflow-hidden rounded-lg border border-border bg-surface',
        className,
      )}
    >
      <header className="flex items-center justify-between border-b border-border
                         px-4 py-3">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="text-base">{icon}</span>
          {href ? (
            <Link to={href} viewTransition aria-label={`Open ${title}`}>
              {heading}
            </Link>
          ) : (
            heading
          )}
        </div>
        {action}
      </header>
      <div className="flex-1 p-4">{children}</div>
    </motion.section>
  );
}
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd frontend && npx vitest run src/components/Panel.test.tsx`
Expected: PASS (both tests).

- [ ] **Step 5: Link the Finance panel**

In `frontend/src/finance/FinancePanel.tsx`, add `href="/finance"` to the `<Panel>` element — change:

```tsx
    <Panel
      title="Finance"
      icon="💹"
```

to:

```tsx
    <Panel
      title="Finance"
      icon="💹"
      href="/finance"
```

- [ ] **Step 6: Run the affected tests + type-check**

Run: `cd frontend && npx vitest run src/components/Panel.test.tsx src/finance/FinancePanel.test.tsx src/routes/Home.test.tsx && npx tsc --noEmit`
Expected: PASS — `FinancePanel.test.tsx` and `Home.test.tsx` already render through `renderWithProviders` (router-wrapped), so the new `<Link>` resolves.

- [ ] **Step 7: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/components/Panel.tsx frontend/src/components/Panel.test.tsx \
  frontend/src/finance/FinancePanel.tsx
git commit -m "feat(finance): link the Finance home panel header to /finance"
```

---

## Task 5: `AssetClassStrip` — the five asset-class mini-cards

A responsive row of five cards (Equities, Crypto, Commodities, Rates, FX), each showing the representative ticker's value, percent change, and a sparkline.

**Files:**
- Create: `frontend/src/finance/AssetClassStrip.tsx`
- Create: `frontend/src/finance/AssetClassStrip.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/finance/AssetClassStrip.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { AssetClassStrip } from './AssetClassStrip';
import type { AssetClass } from '../lib/types';

const assetClasses: AssetClass[] = [
  { label: 'Equities', symbol: '^GSPC', price: 5400, change_pct: 0.4,
    sparkline: [1, 2, 3, 4] },
  { label: 'Crypto', symbol: 'BTC-USD', price: 68000, change_pct: -1.2,
    sparkline: [4, 3, 2, 1] },
];

test('renders a card for each asset class', () => {
  render(<AssetClassStrip assetClasses={assetClasses} />);
  expect(screen.getByText('Equities')).toBeInTheDocument();
  expect(screen.getByText('Crypto')).toBeInTheDocument();
  expect(screen.getByText('+0.40%')).toBeInTheDocument();
  expect(screen.getByText('-1.20%')).toBeInTheDocument();
  expect(screen.getByText('5,400.00')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/finance/AssetClassStrip.test.tsx`
Expected: FAIL — cannot resolve `./AssetClassStrip`.

- [ ] **Step 3: Implement `AssetClassStrip`**

Create `frontend/src/finance/AssetClassStrip.tsx`:

```tsx
import { motion } from 'motion/react';
import type { AssetClass } from '../lib/types';
import { Sparkline } from '../charts/Sparkline';
import { trendColor } from '../charts/colors';
import { formatPercent, formatValue } from '../lib/format';
import { spring } from '../design/motion';

/** The five asset-class mini-cards: Equities, Crypto, Commodities, Rates, FX.
 *  Each shows its representative ticker's value, change, and trend. */
export function AssetClassStrip({
  assetClasses,
}: {
  assetClasses: AssetClass[];
}) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
      {assetClasses.map((ac) => (
        <motion.div
          key={ac.label}
          whileHover={{ y: -2 }}
          transition={spring.snappy}
          className="flex flex-col gap-1 rounded-md border border-border
                     bg-raised px-3 py-2"
        >
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-mono text-[10px] tracking-widest text-ink-mute
                             uppercase">
              {ac.label}
            </span>
            <span
              className="font-mono text-xs tabular-nums"
              style={{ color: trendColor(ac.change_pct) }}
            >
              {formatPercent(ac.change_pct)}
            </span>
          </div>
          <span className="font-mono text-sm tabular-nums text-ink">
            {formatValue(ac.price)}
          </span>
          <Sparkline values={ac.sparkline} width={140} height={28} />
        </motion.div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd frontend && npx vitest run src/finance/AssetClassStrip.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/finance/AssetClassStrip.tsx \
  frontend/src/finance/AssetClassStrip.test.tsx
git commit -m "feat(finance): add AssetClassStrip"
```

---

## Task 6: `IndicesGrid` — the major-indices list

A vertical list of the major indices (S&P 500, Dow, Nasdaq, Russell 2000, VIX); each row shows the index name, sparkline, value, and percent change, and links to the index's drill-down.

**Files:**
- Create: `frontend/src/finance/IndicesGrid.tsx`
- Create: `frontend/src/finance/IndicesGrid.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/finance/IndicesGrid.test.tsx`:

```tsx
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { IndicesGrid } from './IndicesGrid';
import type { WatchlistQuote } from '../lib/types';

const indices: WatchlistQuote[] = [
  { symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.22, volume: 0,
    as_of: '2026-05-20', sparkline: [1, 2, 3, 4] },
  { symbol: '^VIX', price: 14.2, change: -0.3, change_pct: -2.1, volume: 0,
    as_of: '2026-05-20', sparkline: [4, 3, 2, 1] },
];

test('renders each index with a friendly name and a drill-down link', () => {
  renderWithProviders(<IndicesGrid indices={indices} />);
  expect(screen.getByText('S&P 500')).toBeInTheDocument();
  expect(screen.getByText('VIX')).toBeInTheDocument();
  expect(screen.getByText('5,400.00')).toBeInTheDocument();
  const link = screen.getByRole('link', { name: /S&P 500/ });
  expect(link).toHaveAttribute('href', '/finance/%5EGSPC');
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/finance/IndicesGrid.test.tsx`
Expected: FAIL — cannot resolve `./IndicesGrid`.

- [ ] **Step 3: Implement `IndicesGrid`**

Create `frontend/src/finance/IndicesGrid.tsx`:

```tsx
import { Link } from 'react-router-dom';
import type { WatchlistQuote } from '../lib/types';
import { Sparkline } from '../charts/Sparkline';
import { trendColor } from '../charts/colors';
import { formatPercent, formatValue } from '../lib/format';

const INDEX_NAME: Record<string, string> = {
  '^GSPC': 'S&P 500',
  '^DJI': 'Dow Jones',
  '^IXIC': 'Nasdaq',
  '^RUT': 'Russell 2000',
  '^VIX': 'VIX',
};

/** The major indices, each row linking to its drill-down. */
export function IndicesGrid({ indices }: { indices: WatchlistQuote[] }) {
  return (
    <ul className="flex flex-col gap-0.5">
      {indices.map((q) => (
        <li key={q.symbol}>
          <Link
            to={`/finance/${encodeURIComponent(q.symbol)}`}
            viewTransition
            className="flex items-center gap-3 rounded-md px-2 py-1.5
                       transition-colors hover:bg-raised"
          >
            <span className="w-24 font-mono text-xs text-ink">
              {INDEX_NAME[q.symbol] ?? q.symbol}
            </span>
            <Sparkline values={q.sparkline} width={64} height={22} />
            <span className="ml-auto font-mono text-xs tabular-nums text-ink">
              {formatValue(q.price)}
            </span>
            <span
              className="w-16 text-right font-mono text-xs tabular-nums"
              style={{ color: trendColor(q.change_pct) }}
            >
              {formatPercent(q.change_pct)}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd frontend && npx vitest run src/finance/IndicesGrid.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/finance/IndicesGrid.tsx \
  frontend/src/finance/IndicesGrid.test.tsx
git commit -m "feat(finance): add IndicesGrid"
```

---

## Task 7: `TopMovers` — the day's biggest gainers and losers

Two labelled sections (Gainers, Losers); each row shows the ticker, price, and percent change, and links to the instrument drill-down.

**Files:**
- Create: `frontend/src/finance/TopMovers.tsx`
- Create: `frontend/src/finance/TopMovers.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/finance/TopMovers.test.tsx`:

```tsx
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { TopMovers } from './TopMovers';
import type { Mover } from '../lib/types';

const gainers: Mover[] = [
  { symbol: 'NVDA', price: 1200, change_pct: 3.4 },
];
const losers: Mover[] = [
  { symbol: 'INTC', price: 30, change_pct: -2.8 },
];

test('renders the gainers and losers sections', () => {
  renderWithProviders(<TopMovers gainers={gainers} losers={losers} />);
  expect(screen.getByText('Gainers')).toBeInTheDocument();
  expect(screen.getByText('Losers')).toBeInTheDocument();
  expect(screen.getByText('NVDA')).toBeInTheDocument();
  expect(screen.getByText('+3.40%')).toBeInTheDocument();
  expect(screen.getByText('-2.80%')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: /NVDA/ })).toHaveAttribute(
    'href', '/finance/NVDA',
  );
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/finance/TopMovers.test.tsx`
Expected: FAIL — cannot resolve `./TopMovers`.

- [ ] **Step 3: Implement `TopMovers`**

Create `frontend/src/finance/TopMovers.tsx`:

```tsx
import { Link } from 'react-router-dom';
import type { Mover } from '../lib/types';
import { trendColor } from '../charts/colors';
import { formatPercent, formatPrice } from '../lib/format';

function MoverRow({ mover }: { mover: Mover }) {
  return (
    <Link
      to={`/finance/${encodeURIComponent(mover.symbol)}`}
      viewTransition
      className="flex items-center gap-2 rounded-md px-2 py-1
                 transition-colors hover:bg-raised"
    >
      <span className="w-14 font-mono text-xs font-medium text-ink">
        {mover.symbol}
      </span>
      <span className="ml-auto font-mono text-xs tabular-nums text-ink-soft">
        {formatPrice(mover.price)}
      </span>
      <span
        className="w-16 text-right font-mono text-xs tabular-nums"
        style={{ color: trendColor(mover.change_pct) }}
      >
        {formatPercent(mover.change_pct)}
      </span>
    </Link>
  );
}

/** The day's biggest gainers and losers, each linking to its drill-down. */
export function TopMovers({
  gainers, losers,
}: {
  gainers: Mover[];
  losers: Mover[];
}) {
  return (
    <div className="flex flex-col gap-3">
      <section>
        <h3 className="mb-1 font-mono text-[10px] tracking-widest text-up
                       uppercase">
          Gainers
        </h3>
        <div className="flex flex-col gap-0.5">
          {gainers.map((m) => (
            <MoverRow key={m.symbol} mover={m} />
          ))}
        </div>
      </section>
      <section>
        <h3 className="mb-1 font-mono text-[10px] tracking-widest text-down
                       uppercase">
          Losers
        </h3>
        <div className="flex flex-col gap-0.5">
          {losers.map((m) => (
            <MoverRow key={m.symbol} mover={m} />
          ))}
        </div>
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd frontend && npx vitest run src/finance/TopMovers.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/finance/TopMovers.tsx frontend/src/finance/TopMovers.test.tsx
git commit -m "feat(finance): add TopMovers"
```

---

## Task 8: `BreadthInternals` — breadth gauge plus VIX level

Wraps the existing `BreadthGauge` (advance/decline, A/D ratio, up/down counts) and adds the VIX level as a market-internals readout.

**Files:**
- Create: `frontend/src/finance/BreadthInternals.tsx`
- Create: `frontend/src/finance/BreadthInternals.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/finance/BreadthInternals.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { BreadthInternals } from './BreadthInternals';
import type { Breadth, WatchlistQuote } from '../lib/types';

const breadth: Breadth = {
  advancers: 6, decliners: 4, unchanged: 0, advance_decline_ratio: 1.5,
};
const vix: WatchlistQuote = {
  symbol: '^VIX', price: 14.2, change: -0.3, change_pct: -2.1, volume: 0,
  as_of: '2026-05-20', sparkline: [4, 3, 2, 1],
};

test('renders the breadth gauge and the VIX level', () => {
  render(<BreadthInternals breadth={breadth} vix={vix} />);
  expect(screen.getByText(/6 adv/)).toBeInTheDocument();
  expect(screen.getByText('VIX')).toBeInTheDocument();
  expect(screen.getByText('14.20')).toBeInTheDocument();
});

test('omits the VIX block when no VIX quote is available', () => {
  render(<BreadthInternals breadth={breadth} vix={undefined} />);
  expect(screen.queryByText('VIX')).toBeNull();
  expect(screen.getByText(/6 adv/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/finance/BreadthInternals.test.tsx`
Expected: FAIL — cannot resolve `./BreadthInternals`.

- [ ] **Step 3: Implement `BreadthInternals`**

Create `frontend/src/finance/BreadthInternals.tsx`:

```tsx
import type { Breadth, WatchlistQuote } from '../lib/types';
import { BreadthGauge } from './BreadthGauge';
import { trendColor } from '../charts/colors';
import { formatPercent, formatValue } from '../lib/format';

/** Market internals — the advance/decline breadth gauge plus the VIX level.
 *  `vix` is the `^VIX` quote from the markets payload, or undefined. */
export function BreadthInternals({
  breadth, vix,
}: {
  breadth: Breadth;
  vix: WatchlistQuote | undefined;
}) {
  return (
    <div className="flex flex-col gap-4">
      <BreadthGauge breadth={breadth} />
      {vix && (
        <div className="flex items-baseline justify-between border-t
                        border-border pt-3">
          <span className="font-mono text-[10px] tracking-widest text-ink-mute
                           uppercase">
            VIX
          </span>
          <span className="font-mono text-lg tabular-nums text-ink">
            {formatValue(vix.price)}
          </span>
          <span
            className="font-mono text-xs tabular-nums"
            style={{ color: trendColor(vix.change_pct) }}
          >
            {formatPercent(vix.change_pct)}
          </span>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd frontend && npx vitest run src/finance/BreadthInternals.test.tsx`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/finance/BreadthInternals.tsx \
  frontend/src/finance/BreadthInternals.test.tsx
git commit -m "feat(finance): add BreadthInternals"
```

---

## Task 9: `MarketChart` — the hero market chart

A large interactive chart of a selected index. An index switcher (segmented buttons), a timeframe control, and a chart-type toggle drive the existing `PriceChart`. It fetches per-index bars with the existing `useInstrument` hook.

> **Note on timeframes:** the spec text mentions `1D`/`1W` pills, but intraday ranges were deferred during the drill-down build (yfinance's daily backend mapping has no sub-day interval). The hero reuses the existing daily-interval `TimeframeControl` (`1M`/`3M`/`6M`/`1Y`/`5Y`/`MAX`) for consistency with the instrument drill-down.

**Files:**
- Create: `frontend/src/finance/MarketChart.tsx`
- Create: `frontend/src/finance/MarketChart.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/finance/MarketChart.test.tsx`:

```tsx
import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/utils';
import { MarketChart } from './MarketChart';
import type { WatchlistQuote } from '../lib/types';

const bars = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
  open: 100 + i, high: 104 + i, low: 98 + i, close: 102 + i, volume: 1000,
}));

const instrument = {
  symbol: '^GSPC',
  profile: { symbol: '^GSPC', name: 'S&P 500' },
  bars,
  technicals: {
    sma_20: bars.map(() => null), sma_50: bars.map(() => null),
    sma_200: bars.map(() => null), rsi: [], macd_line: [], macd_signal: [],
    macd_histogram: [], bb_upper: [], bb_middle: [], bb_lower: [],
    volume: bars.map(() => 1000),
  },
  stats: {
    momentum_1m: 0, momentum_3m: 0, momentum_6m: 0, volatility_30d: 0,
    week52_high: null, week52_low: null,
  },
  returns: {
    week_1: null, month_1: null, month_3: null, month_6: null, ytd: null,
    year_1: null, year_3: null,
  },
  updated_at: '2026-05-20T20:00:00+00:00',
};

const instrumentFn = vi.fn();
vi.mock('../lib/api', () => ({
  api: { instrument: (s: string, r?: string) => instrumentFn(s, r) },
}));

const indices: WatchlistQuote[] = [
  { symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.2, volume: 0,
    as_of: '2026-05-20', sparkline: [1, 2, 3] },
  { symbol: '^IXIC', price: 17000, change: 60, change_pct: 0.3, volume: 0,
    as_of: '2026-05-20', sparkline: [1, 2, 3] },
];

test('renders the index switcher and the chart controls', async () => {
  instrumentFn.mockResolvedValue(instrument);
  renderWithProviders(<MarketChart indices={indices} />);
  expect(screen.getByRole('group', { name: 'Index' })).toBeInTheDocument();
  expect(screen.getByRole('group', { name: 'Timeframe' })).toBeInTheDocument();
  expect(screen.getByRole('group', { name: 'Chart type' })).toBeInTheDocument();
  await waitFor(() => expect(instrumentFn).toHaveBeenCalledWith('^GSPC', '1y'));
});

test('switching the index refetches for the new symbol', async () => {
  instrumentFn.mockResolvedValue(instrument);
  renderWithProviders(<MarketChart indices={indices} />);
  await userEvent.click(screen.getByRole('button', { name: 'Nasdaq' }));
  await waitFor(() => expect(instrumentFn).toHaveBeenCalledWith('^IXIC', '1y'));
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/finance/MarketChart.test.tsx`
Expected: FAIL — cannot resolve `./MarketChart`.

- [ ] **Step 3: Implement `MarketChart`**

Create `frontend/src/finance/MarketChart.tsx`:

```tsx
import { useState } from 'react';
import { clsx } from 'clsx';
import { useInstrument } from './hooks';
import { PriceChart } from '../charts/PriceChart';
import { ChartTypeToggle, TimeframeControl } from '../charts/ChartControls';
import type { ChartType, Timeframe } from '../charts/ChartControls';
import { PanelSkeleton } from '../components/PanelSkeleton';
import type { WatchlistQuote } from '../lib/types';

const INDEX_NAME: Record<string, string> = {
  '^GSPC': 'S&P 500',
  '^DJI': 'Dow',
  '^IXIC': 'Nasdaq',
  '^RUT': 'Russell 2000',
  '^VIX': 'VIX',
};

/** The hero market chart — pick an index, a timeframe, and a chart type.
 *  Bars come from the shared `useInstrument` hook, which keeps the previous
 *  data while a new index or range loads, so the chart never flashes. */
export function MarketChart({ indices }: { indices: WatchlistQuote[] }) {
  const [symbol, setSymbol] = useState(indices[0]?.symbol ?? '^GSPC');
  const [range, setRange] = useState<Timeframe>('1y');
  const [chartType, setChartType] = useState<ChartType>('area');
  const { data, isLoading, isError } = useInstrument(symbol, range);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <div
          role="group"
          aria-label="Index"
          className="flex gap-0.5 rounded-md border border-border bg-raised p-0.5"
        >
          {indices.map((idx) => (
            <button
              key={idx.symbol}
              type="button"
              aria-pressed={idx.symbol === symbol}
              onClick={() => setSymbol(idx.symbol)}
              className={clsx(
                'rounded px-2 py-0.5 font-mono text-[10px] transition-colors',
                idx.symbol === symbol
                  ? 'bg-accent text-bg'
                  : 'text-ink-mute hover:text-ink',
              )}
            >
              {INDEX_NAME[idx.symbol] ?? idx.symbol}
            </button>
          ))}
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <TimeframeControl value={range} onChange={setRange} />
          <ChartTypeToggle value={chartType} onChange={setChartType} />
        </div>
      </div>

      <div className="mt-3">
        {isLoading && <PanelSkeleton rows={8} />}
        {isError && (
          <p className="py-12 text-center text-sm text-down">
            Couldn't load chart data.
          </p>
        )}
        {data && (
          <PriceChart
            bars={data.bars}
            technicals={data.technicals}
            chartType={chartType}
            showSma={false}
            showBollinger={false}
            height={420}
          />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd frontend && npx vitest run src/finance/MarketChart.test.tsx`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/finance/MarketChart.tsx \
  frontend/src/finance/MarketChart.test.tsx
git commit -m "feat(finance): add MarketChart hero chart"
```

---

## Task 10: `MarketsWatchlist` — the full sortable watchlist table

A multi-column table — Symbol, Price, Change, % Change, Volume, Trend sparkline — with sortable column headers, add/remove, and rows linking to the instrument drill-down. It reads the watchlist from `useOverview` and reuses `useWatchlistMutations`. The compact home-panel `WatchlistTable` is left unchanged.

**Files:**
- Create: `frontend/src/finance/MarketsWatchlist.tsx`
- Create: `frontend/src/finance/MarketsWatchlist.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/finance/MarketsWatchlist.test.tsx`:

```tsx
import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/utils';
import { MarketsWatchlist } from './MarketsWatchlist';
import type { WatchlistQuote } from '../lib/types';

const addWatchlist = vi.fn().mockResolvedValue({ symbols: [] });
const removeWatchlist = vi.fn().mockResolvedValue({ symbols: [] });
vi.mock('../lib/api', () => ({
  api: {
    addWatchlist: (s: string) => addWatchlist(s),
    removeWatchlist: (s: string) => removeWatchlist(s),
  },
}));

const quotes: WatchlistQuote[] = [
  { symbol: 'AAPL', price: 212.5, change: 1.8, change_pct: 0.85,
    volume: 50_000_000, as_of: '2026-05-20', sparkline: [1, 2, 3, 4] },
  { symbol: 'NVDA', price: 1200, change: 30, change_pct: 2.5,
    volume: 40_000_000, as_of: '2026-05-20', sparkline: [4, 3, 2, 1] },
];

/** The symbols, in the order they appear in the table body. */
function rowSymbols(): string[] {
  return screen
    .getAllByRole('link')
    .map((a) => a.textContent ?? '')
    .filter((t) => t === 'AAPL' || t === 'NVDA');
}

test('renders a row for each quote, sorted by % change descending', () => {
  renderWithProviders(<MarketsWatchlist quotes={quotes} />);
  // Default sort: % Change, descending — NVDA (2.5%) before AAPL (0.85%).
  expect(rowSymbols()).toEqual(['NVDA', 'AAPL']);
});

test('clicking the Symbol header sorts alphabetically', async () => {
  renderWithProviders(<MarketsWatchlist quotes={quotes} />);
  await userEvent.click(screen.getByRole('button', { name: /Symbol/ }));
  expect(rowSymbols()).toEqual(['AAPL', 'NVDA']);
});

test('adding a symbol calls the add mutation, upper-cased', async () => {
  renderWithProviders(<MarketsWatchlist quotes={quotes} />);
  await userEvent.type(screen.getByLabelText('Add symbol'), 'tsla');
  await userEvent.click(screen.getByRole('button', { name: 'Add' }));
  await waitFor(() => expect(addWatchlist).toHaveBeenCalledWith('TSLA'));
});

test('removing a symbol calls the remove mutation', async () => {
  renderWithProviders(<MarketsWatchlist quotes={quotes} />);
  await userEvent.click(screen.getByLabelText('Remove AAPL'));
  await waitFor(() => expect(removeWatchlist).toHaveBeenCalledWith('AAPL'));
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/finance/MarketsWatchlist.test.tsx`
Expected: FAIL — cannot resolve `./MarketsWatchlist`.

- [ ] **Step 3: Implement `MarketsWatchlist`**

Create `frontend/src/finance/MarketsWatchlist.tsx`:

```tsx
import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import { clsx } from 'clsx';
import type { WatchlistQuote } from '../lib/types';
import { Sparkline } from '../charts/Sparkline';
import { trendColor } from '../charts/colors';
import {
  formatChange, formatCompact, formatPercent, formatPrice,
} from '../lib/format';
import { useWatchlistMutations } from './hooks';
import { spring } from '../design/motion';

type SortKey = 'symbol' | 'price' | 'change' | 'change_pct' | 'volume';
type SortDir = 'asc' | 'desc';

interface Column {
  key: SortKey;
  label: string;
}

const COLUMNS: Column[] = [
  { key: 'symbol', label: 'Symbol' },
  { key: 'price', label: 'Price' },
  { key: 'change', label: 'Change' },
  { key: 'change_pct', label: '% Change' },
  { key: 'volume', label: 'Volume' },
];

/** The full sortable watchlist table for the Finance domain page. */
export function MarketsWatchlist({ quotes }: { quotes: WatchlistQuote[] }) {
  const { add, remove } = useWatchlistMutations();
  const [draft, setDraft] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('change_pct');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const sorted = useMemo(() => {
    const rows = [...quotes];
    rows.sort((a, b) => {
      const cmp =
        sortKey === 'symbol'
          ? a.symbol.localeCompare(b.symbol)
          : (a[sortKey] as number) - (b[sortKey] as number);
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return rows;
  }, [quotes, sortKey, sortDir]);

  function onSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'symbol' ? 'asc' : 'desc');
    }
  }

  function onAdd(e: FormEvent) {
    e.preventDefault();
    const symbol = draft.trim().toUpperCase();
    if (!symbol) return;
    add.mutate(symbol);
    setDraft('');
  }

  return (
    <div>
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-border">
            {COLUMNS.map((col, i) => (
              <th
                key={col.key}
                className={clsx('px-2 py-1.5', i === 0 ? 'text-left' : 'text-right')}
              >
                <button
                  type="button"
                  onClick={() => onSort(col.key)}
                  className={clsx(
                    'font-mono text-[10px] tracking-widest uppercase',
                    'transition-colors',
                    sortKey === col.key
                      ? 'text-accent'
                      : 'text-ink-mute hover:text-ink',
                  )}
                >
                  {col.label}
                  {sortKey === col.key && (
                    <span aria-hidden="true">
                      {sortDir === 'asc' ? ' ↑' : ' ↓'}
                    </span>
                  )}
                </button>
              </th>
            ))}
            <th className="px-2 py-1.5 text-right">
              <span className="font-mono text-[10px] tracking-widest
                               text-ink-mute uppercase">
                Trend
              </span>
            </th>
            <th aria-label="Actions" className="w-8" />
          </tr>
        </thead>
        <tbody>
          <AnimatePresence initial={false}>
            {sorted.map((q) => (
              <motion.tr
                key={q.symbol}
                layout
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={spring.snappy}
                className="group border-b border-border transition-colors
                           hover:bg-raised"
              >
                <td className="px-2 py-1.5">
                  <Link
                    to={`/finance/${encodeURIComponent(q.symbol)}`}
                    viewTransition
                    className="font-mono text-xs font-medium text-ink
                               transition-colors hover:text-accent"
                  >
                    {q.symbol}
                  </Link>
                </td>
                <td className="px-2 py-1.5 text-right font-mono text-xs
                               tabular-nums text-ink">
                  {formatPrice(q.price)}
                </td>
                <td
                  className="px-2 py-1.5 text-right font-mono text-xs tabular-nums"
                  style={{ color: trendColor(q.change) }}
                >
                  {formatChange(q.change)}
                </td>
                <td
                  className="px-2 py-1.5 text-right font-mono text-xs tabular-nums"
                  style={{ color: trendColor(q.change_pct) }}
                >
                  {formatPercent(q.change_pct)}
                </td>
                <td className="px-2 py-1.5 text-right font-mono text-xs
                               tabular-nums text-ink-soft">
                  {formatCompact(q.volume)}
                </td>
                <td className="px-2 py-1.5">
                  <div className="flex justify-end">
                    <Sparkline values={q.sparkline} width={72} height={22} />
                  </div>
                </td>
                <td className="px-2 py-1.5 text-right">
                  <button
                    type="button"
                    onClick={() => remove.mutate(q.symbol)}
                    aria-label={`Remove ${q.symbol}`}
                    className="text-ink-mute opacity-0 transition-opacity
                               hover:text-down group-hover:opacity-100"
                  >
                    ✕
                  </button>
                </td>
              </motion.tr>
            ))}
          </AnimatePresence>
        </tbody>
      </table>

      <form onSubmit={onAdd} className="mt-3 flex gap-1">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add symbol…"
          aria-label="Add symbol"
          className="min-w-0 flex-1 rounded-md border border-border bg-raised
                     px-2 py-1 text-xs text-ink uppercase outline-none
                     transition-colors focus:border-accent"
        />
        <button
          type="submit"
          className="rounded-md border border-border px-3 py-1 text-xs
                     text-ink-soft transition-colors hover:border-border-strong"
        >
          Add
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd frontend && npx vitest run src/finance/MarketsWatchlist.test.tsx`
Expected: PASS (all four tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/finance/MarketsWatchlist.tsx \
  frontend/src/finance/MarketsWatchlist.test.tsx
git commit -m "feat(finance): add sortable MarketsWatchlist table"
```

---

## Task 11: `FinanceRoute` — assemble the `/finance` bento page

The domain page itself: breadcrumb, loading/error/stale handling, and the bento grid wiring all the tiles together. The watchlist tile reads `useOverview` (the watchlist lives in the overview payload, not the markets payload).

**Files:**
- Create: `frontend/src/routes/FinanceRoute.tsx`
- Create: `frontend/src/routes/FinanceRoute.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/routes/FinanceRoute.test.tsx`:

```tsx
import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { FinanceRoute } from './FinanceRoute';

const bars = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
  open: 100 + i, high: 104 + i, low: 98 + i, close: 102 + i, volume: 1000,
}));

const markets = {
  asset_classes: [
    { label: 'Equities', symbol: '^GSPC', price: 5400, change_pct: 0.4,
      sparkline: [1, 2, 3, 4] },
    { label: 'Crypto', symbol: 'BTC-USD', price: 68000, change_pct: -1.2,
      sparkline: [4, 3, 2, 1] },
  ],
  indices: [
    { symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.22, volume: 0,
      as_of: '2026-05-20', sparkline: [1, 2, 3, 4] },
    { symbol: '^VIX', price: 14.2, change: -0.3, change_pct: -2.1, volume: 0,
      as_of: '2026-05-20', sparkline: [4, 3, 2, 1] },
  ],
  gainers: [{ symbol: 'NVDA', price: 1200, change_pct: 3.4 }],
  losers: [{ symbol: 'INTC', price: 30, change_pct: -2.8 }],
  sectors: [{ symbol: 'XLK', name: 'Technology', change_pct: 1.1 }],
  breadth: { advancers: 6, decliners: 4, unchanged: 0, advance_decline_ratio: 1.5 },
  updated_at: '2026-05-21T20:00:00+00:00',
};

const overview = {
  watchlist: [
    { symbol: 'AAPL', price: 212.5, change: 1.8, change_pct: 0.85,
      volume: 50_000_000, as_of: '2026-05-20', sparkline: [1, 2, 3, 4] },
  ],
  indices: [],
  sectors: [],
  breadth: { advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0 },
  updated_at: '2026-05-21T20:00:00+00:00',
};

const instrument = {
  symbol: '^GSPC',
  profile: { symbol: '^GSPC', name: 'S&P 500' },
  bars,
  technicals: {
    sma_20: bars.map(() => null), sma_50: bars.map(() => null),
    sma_200: bars.map(() => null), rsi: [], macd_line: [], macd_signal: [],
    macd_histogram: [], bb_upper: [], bb_middle: [], bb_lower: [],
    volume: bars.map(() => 1000),
  },
  stats: {
    momentum_1m: 0, momentum_3m: 0, momentum_6m: 0, volatility_30d: 0,
    week52_high: null, week52_low: null,
  },
  returns: {
    week_1: null, month_1: null, month_3: null, month_6: null, ytd: null,
    year_1: null, year_3: null,
  },
  updated_at: '2026-05-20T20:00:00+00:00',
};

vi.mock('../lib/api', () => ({
  api: {
    markets: vi.fn().mockResolvedValue(markets),
    overview: vi.fn().mockResolvedValue(overview),
    instrument: vi.fn().mockResolvedValue(instrument),
    addWatchlist: vi.fn(),
    removeWatchlist: vi.fn(),
  },
}));

test('renders the bento grid of market tiles', async () => {
  renderWithProviders(<FinanceRoute />, { route: '/finance', path: '/finance' });
  await waitFor(() =>
    expect(screen.getByText('Asset Classes')).toBeInTheDocument(),
  );
  expect(screen.getByText('Market Chart')).toBeInTheDocument();
  expect(screen.getByText('Top Movers')).toBeInTheDocument();
  expect(screen.getByText('Watchlist')).toBeInTheDocument();
  // Data from the tiles.
  expect(screen.getByText('Equities')).toBeInTheDocument();
  expect(screen.getByText('NVDA')).toBeInTheDocument();
  await waitFor(() =>
    expect(screen.getByText('AAPL')).toBeInTheDocument(),
  );
});

test('shows an error message when the markets payload fails', async () => {
  const { api } = await import('../lib/api');
  vi.mocked(api.markets).mockRejectedValueOnce(new Error('boom'));
  renderWithProviders(<FinanceRoute />, { route: '/finance', path: '/finance' });
  await waitFor(() =>
    expect(screen.getByText(/Couldn't load market data/)).toBeInTheDocument(),
  );
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npx vitest run src/routes/FinanceRoute.test.tsx`
Expected: FAIL — cannot resolve `./FinanceRoute`.

- [ ] **Step 3: Implement `FinanceRoute`**

Create `frontend/src/routes/FinanceRoute.tsx`:

```tsx
import { AppShell } from '../components/AppShell';
import { Breadcrumb } from '../components/Breadcrumb';
import { BentoGrid, BentoTile } from '../components/BentoGrid';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { useMarkets, useOverview } from '../finance/hooks';
import { AssetClassStrip } from '../finance/AssetClassStrip';
import { MarketChart } from '../finance/MarketChart';
import { BreadthInternals } from '../finance/BreadthInternals';
import { IndicesGrid } from '../finance/IndicesGrid';
import { TopMovers } from '../finance/TopMovers';
import { SectorHeatmap } from '../finance/SectorHeatmap';
import { MarketsWatchlist } from '../finance/MarketsWatchlist';
import { formatUpdated } from '../lib/format';

/** The Finance domain page — a bento grid of market tiles. */
export function FinanceRoute() {
  const { data, isLoading, isError, isStale } = useMarkets();
  const overview = useOverview();
  const vix = data?.indices.find((q) => q.symbol === '^VIX');

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-6xl p-4">
        <div className="flex items-center justify-between gap-3">
          <Breadcrumb
            trail={[{ label: 'Dashboard', to: '/' }, { label: 'Finance' }]}
          />
          {data && (
            <span className="font-mono text-[10px] text-ink-mute">
              {isStale ? 'Stale · ' : ''}
              {formatUpdated(data.updated_at)}
            </span>
          )}
        </div>

        {isLoading && (
          <div className="mt-4">
            <PanelSkeleton rows={12} />
          </div>
        )}

        {isError && (
          <p className="mt-8 text-center text-sm text-down">
            Couldn't load market data.
          </p>
        )}

        {data && (
          <div className="mt-4">
            <BentoGrid>
              <BentoTile title="Asset Classes" colSpan={6}>
                <AssetClassStrip assetClasses={data.asset_classes} />
              </BentoTile>

              <BentoTile title="Market Chart" colSpan={4}>
                <MarketChart indices={data.indices} />
              </BentoTile>

              <BentoTile title="Internals" colSpan={2}>
                <BreadthInternals breadth={data.breadth} vix={vix} />
              </BentoTile>

              <BentoTile title="Indices" colSpan={2}>
                <IndicesGrid indices={data.indices} />
              </BentoTile>

              <BentoTile title="Top Movers" colSpan={2}>
                <TopMovers gainers={data.gainers} losers={data.losers} />
              </BentoTile>

              {/* No tile title — SectorHeatmap renders its own header with a
                  live hover readout. */}
              <BentoTile colSpan={2}>
                <SectorHeatmap sectors={data.sectors} />
              </BentoTile>

              <BentoTile title="Watchlist" colSpan={6}>
                {overview.data ? (
                  <MarketsWatchlist quotes={overview.data.watchlist} />
                ) : (
                  <PanelSkeleton rows={4} />
                )}
              </BentoTile>
            </BentoGrid>
          </div>
        )}
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 4: Run it to confirm it passes**

Run: `cd frontend && npx vitest run src/routes/FinanceRoute.test.tsx`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/routes/FinanceRoute.tsx \
  frontend/src/routes/FinanceRoute.test.tsx
git commit -m "feat(finance): add the /finance bento domain page"
```

---

## Task 12: Register the `/finance` route, add the palette destination, E2E

Wire the route into the router, add `/finance` to the command palette, and add a Playwright spec covering home → `/finance` → instrument drill-down.

**Files:**
- Modify: `frontend/src/router.tsx`
- Modify: `frontend/src/components/CommandPalette.tsx`
- Create: `frontend/e2e/finance-domain.spec.ts`

- [ ] **Step 1: Register the route**

Replace the contents of `frontend/src/router.tsx` with:

```tsx
import { createBrowserRouter } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { Home } from './routes/Home';
import { FinanceRoute } from './routes/FinanceRoute';
import { InstrumentRoute } from './routes/InstrumentRoute';
import { IndicatorRoute } from './routes/IndicatorRoute';

export const routes: RouteObject[] = [
  { path: '/', element: <Home /> },
  { path: '/finance', element: <FinanceRoute /> },
  { path: '/finance/:symbol', element: <InstrumentRoute /> },
  { path: '/economics/:seriesId', element: <IndicatorRoute /> },
];

export const router = createBrowserRouter(routes);
```

- [ ] **Step 2: Add the command-palette destination**

In `frontend/src/components/CommandPalette.tsx`, add one entry to the `STATIC_DESTINATIONS` array, directly after the `Dashboard` entry:

```tsx
  { label: 'Dashboard', hint: 'Home', to: '/' },
  { label: 'Finance Markets', hint: 'Page', to: '/finance' },
```

- [ ] **Step 3: Type-check and run the full unit suite**

Run: `cd frontend && npx tsc --noEmit && npx vitest run`
Expected: PASS — all unit tests green, no type errors.

- [ ] **Step 4: Write the Playwright E2E spec**

Create `frontend/e2e/finance-domain.spec.ts`:

```ts
import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

function makeBars(n: number) {
  const bars = [];
  let price = 180;
  for (let i = 0; i < n; i++) {
    price += Math.sin(i / 7) * 2;
    bars.push({
      date: new Date(Date.UTC(2024, 0, 1 + i)).toISOString().slice(0, 10),
      open: price, high: price + 3, low: price - 3, close: price + 1,
      volume: 1_000_000,
    });
  }
  return bars;
}

const bars = makeBars(120);

const overview = {
  watchlist: [
    {
      symbol: 'AAPL', price: 212.5, change: 1.8, change_pct: 0.85,
      volume: 50_000_000, as_of: '2026-05-20',
      sparkline: [205, 207, 206, 209, 211, 210, 212.5],
    },
  ],
  indices: [
    {
      symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.22,
      volume: 0, as_of: '2026-05-20',
    },
  ],
  sectors: [{ symbol: 'XLK', name: 'Technology', change_pct: 1.1 }],
  breadth: { advancers: 2, decliners: 0, unchanged: 0, advance_decline_ratio: 2 },
  updated_at: '2026-05-20T20:00:00+00:00',
};

const markets = {
  asset_classes: [
    { label: 'Equities', symbol: '^GSPC', price: 5400, change_pct: 0.4,
      sparkline: [1, 2, 3, 4] },
    { label: 'Crypto', symbol: 'BTC-USD', price: 68000, change_pct: -1.2,
      sparkline: [4, 3, 2, 1] },
  ],
  indices: [
    { symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.22, volume: 0,
      as_of: '2026-05-20', sparkline: [1, 2, 3, 4] },
    { symbol: '^IXIC', price: 17000, change: 60, change_pct: 0.35, volume: 0,
      as_of: '2026-05-20', sparkline: [1, 2, 3, 4] },
    { symbol: '^VIX', price: 14.2, change: -0.3, change_pct: -2.1, volume: 0,
      as_of: '2026-05-20', sparkline: [4, 3, 2, 1] },
  ],
  gainers: [{ symbol: 'NVDA', price: 1200, change_pct: 3.4 }],
  losers: [{ symbol: 'INTC', price: 30, change_pct: -2.8 }],
  sectors: [{ symbol: 'XLK', name: 'Technology', change_pct: 1.1 }],
  breadth: { advancers: 6, decliners: 4, unchanged: 0, advance_decline_ratio: 1.5 },
  updated_at: '2026-05-21T20:00:00+00:00',
};

const instrument = {
  symbol: 'AAPL',
  profile: {
    symbol: 'AAPL', name: 'Apple Inc.', sector: 'Technology',
    industry: 'Consumer Electronics', market_cap: 3.21e12, pe_ratio: 29.4,
    price_to_book: 48.1, dividend_yield: 0.5, week52_high: 240,
    week52_low: 160, beta: 1.2,
  },
  bars,
  technicals: {
    sma_20: bars.map((b) => b.close),
    sma_50: bars.map((b) => b.close),
    sma_200: bars.map(() => null),
    rsi: bars.map((_, i) => (i < 14 ? null : 55)),
    macd_line: bars.map((_, i) => (i < 26 ? null : 0.4)),
    macd_signal: bars.map((_, i) => (i < 26 ? null : 0.2)),
    macd_histogram: bars.map((_, i) => (i < 26 ? null : 0.2)),
    bb_upper: bars.map((b) => b.close + 5),
    bb_middle: bars.map((b) => b.close),
    bb_lower: bars.map((b) => b.close - 5),
    volume: bars.map(() => 1000),
  },
  stats: {
    momentum_1m: 4.2, momentum_3m: 9.1, momentum_6m: 15.3,
    volatility_30d: 22.5, week52_high: 240, week52_low: 160,
  },
  returns: {
    week_1: 1.2, month_1: -3.4, month_3: 8.0, month_6: 12.5,
    ytd: 6.1, year_1: 22.0, year_3: null,
  },
  updated_at: '2026-05-20T20:00:00+00:00',
};

async function stubApi(page: Page) {
  await page.route('**/api/auth/status', (route) =>
    route.fulfill({ json: { auth_enabled: false } }),
  );
  await page.route('**/api/finance/overview', (route) =>
    route.fulfill({ json: overview }),
  );
  await page.route('**/api/finance/markets', (route) =>
    route.fulfill({ json: markets }),
  );
  await page.route('**/api/finance/instrument/**', (route) =>
    route.fulfill({ json: instrument }),
  );
}

test('home links into the Finance domain page and drills down', async ({
  page,
}) => {
  await stubApi(page);
  await page.goto('/');

  // The Finance panel header links to the domain page.
  await page.getByRole('link', { name: 'Open Finance' }).click();
  await expect(page).toHaveURL(/\/finance$/);

  // The bento tiles render.
  await expect(page.getByText('Asset Classes')).toBeVisible();
  await expect(page.getByText('Top Movers')).toBeVisible();
  await expect(page.getByText('Watchlist')).toBeVisible();
  await expect(page.getByRole('group', { name: 'Index' })).toBeVisible();

  // Switching the hero index works.
  await page.getByRole('button', { name: 'Nasdaq' }).click();
  await expect(page.getByRole('button', { name: 'Nasdaq' })).toHaveAttribute(
    'aria-pressed', 'true',
  );

  // A top mover drills down to its instrument page.
  await page.getByRole('link', { name: /NVDA/ }).click();
  await expect(page).toHaveURL(/\/finance\/NVDA$/);
  await expect(page.getByRole('heading', { name: 'AAPL' })).toBeVisible();
});
```

> Note: the instrument stub returns the AAPL fixture for every symbol (the `instrument/**` route match is symbol-agnostic), so after clicking `NVDA` the drill-down heading reads `AAPL` — that is expected for this stub.

- [ ] **Step 5: Run the E2E suite**

Run: `cd frontend && npx playwright test`
Expected: PASS — both the existing `overview-to-drilldown` spec and the new `finance-domain` spec are green.

If Playwright browsers are not installed, run `npx playwright install` first.

- [ ] **Step 6: Production build check**

Run: `cd frontend && npm run build`
Expected: build succeeds with no type errors.

- [ ] **Step 7: Commit**

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard
git add frontend/src/router.tsx frontend/src/components/CommandPalette.tsx \
  frontend/e2e/finance-domain.spec.ts
git commit -m "feat(finance): register /finance route, palette entry, E2E spec"
```

---

## Final verification

After all 12 tasks, run the full suite once more from `frontend/`:

```bash
cd /Users/ajaiupadhyaya/Documents/news-dashboard/frontend
npx tsc --noEmit && npx vitest run && npm run build && npx playwright test
```

All must pass: type-check clean, every Vitest test green, production build successful, both Playwright specs green.

---

## Plan self-review notes

- **Spec coverage (§5.1):** hero market chart → Task 9; asset-class tiles → Task 5; indices grid → Task 6; top movers → Task 7; sector heatmap → reused directly in Task 11; breadth & internals → Task 8; sortable watchlist → Task 10; the bento page assembling them → Task 11. Shared foundations `BentoGrid` (§4) → Task 2, `Breadcrumb` (§4) → Task 3. Home panel header link (§4) → Task 4. Command palette domain destination (§7.1) → Task 12. Route registration (§4) → Task 12.
- **Out of scope for this plan (intentionally):** the instrument drill-down enrichment (§5.2) and the Finance backend (§5.3) — both already built and merged. Economics (§6) is a separate plan. Intraday `1D`/`1W` ranges remain deferred (documented in Task 9).
- **Type consistency:** `MarketsResponse` field names (`asset_classes`, `gainers`, `losers`, `indices`, `sectors`, `breadth`) match `backend/app/models.py`. `AssetClass`/`Mover` mirror the backend exactly. `Timeframe`/`ChartType` are imported from the existing `charts/ChartControls.tsx`. `useInstrument(symbol, range)` and `useWatchlistMutations()` signatures match `finance/hooks.ts`.
- **Reuse:** `Sparkline`, `PriceChart`, `ChartControls`, `SectorHeatmap`, `BreadthGauge`, `PanelSkeleton`, `AppShell`, `useInstrument`, `useOverview`, `useWatchlistMutations`, `trendColor`, `formatPrice`/`formatPercent`/`formatChange`/`formatCompact`/`formatUpdated` are all reused, not duplicated.
