# Phase 1b — Frontend Foundation & Finance UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React SPA — a four-quadrant dashboard shell plus the Finance domain end-to-end (overview panel + instrument drill-down) — against the Phase 1a backend API, establishing the design-token, motion, and chart systems.

**Architecture:** A Vite + React + TypeScript single-page app under `frontend/`. A CSS-first design-token layer (Tailwind v4 `@theme`) and a small motion-preset module define the visual language. A bespoke D3-in-React chart system (responsive frame, axes, sparkline, candlestick) renders all visualizations. TanStack Query owns data fetching/caching against the backend; React Router v7 owns routing, with the View Transitions API morphing the overview into the drill-down. The frontend never blocks on third-party APIs — it reads the backend's pre-computed, cached endpoints.

**Tech Stack:** Vite, React 19, TypeScript, Tailwind CSS v4, Motion (Framer Motion) `motion/react`, D3 (d3-scale/shape/array/format/time-format), TanStack Query v5, React Router v7, Vitest + Testing Library, Playwright.

---

## Context for the implementer

You are building the frontend for the **News & Markets Dashboard**. The backend (Phase 1a) is already complete and merged — a FastAPI app under `backend/`. This plan creates a **new `frontend/` directory** at the repo root, a sibling of `backend/`.

### Design bar (hard requirement — not polish-if-time)

The product must look **simple and calm on the surface, and stunning the moment it is interacted with**. Every chart is bespoke — professional and legible first, then creative. Hover/focus/selection states animate with spring physics. The overview morphs into the drill-down via a shared-element transition. All motion honors `prefers-reduced-motion`. These behaviors are built into the tasks below; do not skip them.

### Backend API contract (already built — do not change the backend)

Base URL in dev: `http://127.0.0.1:8000`. All `/api/finance/*` and `/api/watchlist/*` routes require a bearer token **only when the backend has `DASHBOARD_TOKEN` set**; `/api/auth/status` reports whether auth is required.

| Method & path | Auth | Response shape |
|---|---|---|
| `GET /health` | no | `{ "status": "ok" }` |
| `GET /api/auth/status` | no | `{ "auth_enabled": boolean }` |
| `POST /api/auth/login` body `{password}` | no | `{ "token": string }` |
| `GET /api/finance/overview` | yes | `OverviewResponse` |
| `GET /api/finance/instrument/{symbol}` | yes | `InstrumentResponse` (404 if no data) |
| `GET /api/watchlist` | yes | `{ "symbols": string[] }` |
| `POST /api/watchlist` body `{symbol}` | yes | `{ "symbols": string[] }` |
| `DELETE /api/watchlist/{symbol}` | yes | `{ "symbols": string[] }` |

**Response shapes** (field names and types are exact — mirror them precisely):

```
Bar              = { date: str(ISO date), open, high, low, close: float, volume: int }
Quote            = { symbol: str, price, change, change_pct: float, volume: int, as_of: str }
WatchlistQuote   = Quote + { sparkline: float[] }            # sparkline is 24 points
Fundamentals     = { symbol, name: str, sector, industry: str|null,
                     market_cap, pe_ratio, price_to_book, dividend_yield,
                     week52_high, week52_low, beta: float|null }
SectorChange     = { symbol, name: str, change_pct: float }
Breadth          = { advancers, decliners, unchanged: int, advance_decline_ratio: float }
OverviewResponse = { watchlist: WatchlistQuote[], indices: Quote[],
                     sectors: SectorChange[], breadth: Breadth, updated_at: str }
Technicals       = { sma_20, sma_50, sma_200: (float|null)[] }   # aligned to bars
InstrumentStats  = { momentum_1m, momentum_3m, momentum_6m, volatility_30d: float,
                     week52_high, week52_low: float|null }
InstrumentResponse = { symbol: str, profile: Fundamentals, bars: Bar[],
                       technicals: Technicals, stats: InstrumentStats, updated_at: str }
```

**Critical semantics — do not get these wrong:**
- `change_pct`, `momentum_1m/3m/6m`, and `volatility_30d` are **already percent numbers** (e.g. `1.23` means 1.23%). Never multiply by 100 again.
- `Bar.date` and `Quote.as_of` are **date-only** strings (`"2026-05-20"`). Format them with a **UTC** formatter to avoid off-by-one days.
- `updated_at` is a **full ISO datetime** with offset (`"2026-05-20T20:00:00+00:00"`). Format in local time.
- `Technicals.sma_*` arrays are the **same length as `bars`**, with leading `null`s until each window fills.
- Index/sector symbols may begin with `^` (e.g. `^GSPC`). Always `encodeURIComponent` symbols in URLs.

### Running the app end-to-end (manual smoke test)

1. Backend: `cd backend && uvicorn app.main:app` (defaults to port 8000). Default `CORS_ORIGINS=*` already allows the Vite dev server.
2. Frontend: `cd frontend && npm run dev` (port 5173).

All automated tests (Vitest unit/component, Playwright E2E) mock the backend — they do **not** require the backend to be running.

### File structure (created by this plan)

```
frontend/
  package.json  vite.config.ts  tsconfig.json  index.html
  .gitignore  .env.example  README.md  playwright.config.ts
  src/
    main.tsx                 App.tsx              index.css
    vite-env.d.ts            router.tsx
    design/
      tokens.ts              # JS-accessible token values (for D3/charts)
      motion.ts              # spring presets, durations, enter variants
    lib/
      types.ts               # TS mirrors of the API response shapes
      api.ts                 # fetch client + endpoint functions
      format.ts              # number/percent/date formatters (pure)
      queryClient.ts         # TanStack Query client
      useReducedMotion.ts    # reduced-motion hooks
    auth/
      AuthContext.tsx        AuthGate.tsx         LoginScreen.tsx
    charts/
      useChartDimensions.ts  ChartFrame.tsx       Axis.tsx
      colors.ts              Sparkline.tsx        CandlestickChart.tsx
    components/
      AppShell.tsx  AppBar.tsx  BriefingRibbon.tsx  QuadrantGrid.tsx
      Panel.tsx     ComingSoonPanel.tsx           PanelSkeleton.tsx
    finance/
      hooks.ts               FinancePanel.tsx     WatchlistTable.tsx
      BreadthGauge.tsx       SectorHeatmap.tsx    IndexStrip.tsx
      FundamentalsGrid.tsx   StatsRow.tsx
    routes/
      Home.tsx               InstrumentRoute.tsx
    test/
      setup.ts               utils.tsx
  e2e/
    overview-to-drilldown.spec.ts
```

**Run all npm commands from inside `frontend/`.** Each task's commit step adds only the files that task touched.

---

## Task 1: Scaffold the Vite + React + TypeScript project

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/.gitignore`, `frontend/.env.example`, `frontend/README.md`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`, `frontend/src/vite-env.d.ts`
- Create: `frontend/src/test/setup.ts`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Create the project directory and a minimal `package.json`**

Create `frontend/package.json`:

```json
{
  "name": "news-dashboard-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "lint": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test"
  }
}
```

- [ ] **Step 2: Install dependencies**

Run from `frontend/`:

```bash
npm install react react-dom react-router-dom @tanstack/react-query motion clsx \
  d3-scale d3-shape d3-array d3-format d3-time-format \
  @fontsource-variable/inter @fontsource-variable/jetbrains-mono

npm install -D vite @vitejs/plugin-react typescript \
  @types/react @types/react-dom \
  @types/d3-scale @types/d3-shape @types/d3-array @types/d3-format @types/d3-time-format \
  tailwindcss @tailwindcss/vite \
  vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event \
  @playwright/test
```

If any package's latest version is incompatible, install the latest of that major version. npm writes the resolved versions into `package.json`.

- [ ] **Step 3: Create config files**

`frontend/vite.config.ts`:

```ts
/// <reference types="vitest/config" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    css: true,
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
  },
});
```

`frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src", "vite.config.ts", "playwright.config.ts", "e2e"]
}
```

`frontend/index.html`:

```html
<!doctype html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="color-scheme" content="dark" />
    <title>News &amp; Markets Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`frontend/.gitignore`:

```
node_modules/
dist/
dist-ssr/
*.local
.env
coverage/
playwright-report/
test-results/
.vite/
```

`frontend/.env.example`:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

`frontend/README.md`:

```markdown
# News & Markets Dashboard — Frontend

React + TypeScript SPA for the News & Markets Dashboard.

## Setup

    npm install
    cp .env.example .env

## Scripts

- `npm run dev` — dev server on http://localhost:5173
- `npm run build` — type-check and production build
- `npm test` — unit & component tests (Vitest)
- `npm run test:e2e` — end-to-end tests (Playwright)

The backend (`../backend`) must be running for live data; tests mock it.
```

- [ ] **Step 4: Create source entry files**

`frontend/src/vite-env.d.ts`:

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
}
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

`frontend/src/index.css`:

```css
@import "tailwindcss";
```

`frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

`frontend/src/App.tsx`:

```tsx
export default function App() {
  return <div>News &amp; Markets Dashboard</div>;
}
```

`frontend/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 5: Write the failing test**

`frontend/src/App.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the app name', () => {
  render(<App />);
  expect(screen.getByText(/News & Markets Dashboard/i)).toBeInTheDocument();
});
```

- [ ] **Step 6: Run the test**

Run: `npm test`
Expected: PASS (1 test).

- [ ] **Step 7: Verify the build and type-check**

Run: `npm run build`
Expected: type-check passes and Vite produces a `dist/` bundle with no errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts \
  frontend/tsconfig.json frontend/index.html frontend/.gitignore \
  frontend/.env.example frontend/README.md frontend/src
git commit -m "feat(frontend): scaffold Vite + React + TypeScript project"
```

---

## Task 2: Design-token layer and global styles

**Files:**
- Modify: `frontend/src/index.css` (replace entire file)
- Create: `frontend/src/design/tokens.ts`
- Test: `frontend/src/design/tokens.test.ts`

- [ ] **Step 1: Write the failing test**

`frontend/src/design/tokens.test.ts`:

```ts
import { tokens } from './tokens';

test('exposes the semantic color palette', () => {
  expect(tokens.color.up).toBe('#3fb950');
  expect(tokens.color.down).toBe('#f0506a');
  expect(tokens.color.accent).toBe('#5b9dff');
});

test('exposes surface and ink colors used by charts', () => {
  for (const key of ['bg', 'surface', 'raised', 'border', 'ink', 'inkSoft', 'inkMute']) {
    expect(tokens.color[key as keyof typeof tokens.color]).toMatch(/^#[0-9a-f]{6}$/i);
  }
});

test('exposes font stacks', () => {
  expect(tokens.font.mono).toContain('JetBrains Mono');
  expect(tokens.font.sans).toContain('Inter');
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- tokens`
Expected: FAIL — `./tokens` does not exist.

- [ ] **Step 3: Create the token module**

`frontend/src/design/tokens.ts`:

```ts
/**
 * Design tokens, mirrored here in TypeScript so D3/SVG code (which renders
 * attributes, not classes) can use the exact same palette as the CSS in
 * `index.css`. The CSS `@theme` block is the source of truth for Tailwind
 * utilities; this object is the source of truth for chart code. Keep them
 * in sync when colors change.
 */
export const tokens = {
  color: {
    bg: '#0a0c10',
    surface: '#12151c',
    raised: '#171b24',
    border: '#232834',
    borderStrong: '#2f3645',
    ink: '#e6e9ef',
    inkSoft: '#9aa3b2',
    inkMute: '#5f6878',
    accent: '#5b9dff',
    up: '#3fb950',
    down: '#f0506a',
    flat: '#8b94a3',
  },
  font: {
    sans: '"Inter Variable", system-ui, -apple-system, sans-serif',
    mono: '"JetBrains Mono Variable", ui-monospace, "SF Mono", monospace',
  },
} as const;
```

- [ ] **Step 4: Replace `index.css` with the full token layer and global styles**

`frontend/src/index.css` (replace the whole file):

```css
@import "tailwindcss";
@import "@fontsource-variable/inter";
@import "@fontsource-variable/jetbrains-mono";

@theme {
  /* surfaces */
  --color-bg: #0a0c10;
  --color-surface: #12151c;
  --color-raised: #171b24;
  --color-border: #232834;
  --color-border-strong: #2f3645;

  /* text */
  --color-ink: #e6e9ef;
  --color-ink-soft: #9aa3b2;
  --color-ink-mute: #5f6878;

  /* brand + semantic */
  --color-accent: #5b9dff;
  --color-up: #3fb950;
  --color-down: #f0506a;
  --color-flat: #8b94a3;

  /* typography */
  --font-sans: "Inter Variable", system-ui, -apple-system, sans-serif;
  --font-mono: "JetBrains Mono Variable", ui-monospace, "SF Mono", monospace;

  /* radii */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
}

@layer base {
  html, body, #root { height: 100%; }

  body {
    margin: 0;
    background: var(--color-bg);
    color: var(--color-ink);
    font-family: var(--font-sans);
    -webkit-font-smoothing: antialiased;
  }

  ::selection {
    background: color-mix(in srgb, var(--color-accent) 32%, transparent);
  }

  *:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
    border-radius: var(--radius-sm);
  }

  /* Respect reduced-motion for CSS transitions/animations and for the
     View Transitions API morphs used between overview and drill-down. */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
    ::view-transition-group(*),
    ::view-transition-old(*),
    ::view-transition-new(*) {
      animation: none !important;
    }
  }
}
```

- [ ] **Step 5: Run the test**

Run: `npm test -- tokens`
Expected: PASS (3 tests).

- [ ] **Step 6: Verify the build**

Run: `npm run build`
Expected: build succeeds (Tailwind compiles the `@theme` block, fonts resolve).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/index.css frontend/src/design/tokens.ts frontend/src/design/tokens.test.ts
git commit -m "feat(frontend): design-token layer and global styles"
```

---

## Task 3: Motion system

**Files:**
- Create: `frontend/src/design/motion.ts`
- Create: `frontend/src/lib/useReducedMotion.ts`
- Modify: `frontend/src/test/setup.ts` (add `matchMedia` mock)
- Modify: `frontend/src/App.tsx` (wrap in `MotionConfig`)
- Test: `frontend/src/design/motion.test.ts`, `frontend/src/lib/useReducedMotion.test.tsx`

- [ ] **Step 1: Add a `matchMedia` mock to the test setup**

`frontend/src/test/setup.ts` (replace the whole file):

```ts
import '@testing-library/jest-dom/vitest';

// jsdom does not implement matchMedia; motion's reduced-motion hook needs it.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }),
});
```

- [ ] **Step 2: Write the failing test**

`frontend/src/design/motion.test.ts`:

```ts
import { spring, duration, fadeRise } from './motion';

test('spring presets are spring-typed transitions', () => {
  for (const preset of [spring.smooth, spring.snappy, spring.gentle]) {
    expect(preset.type).toBe('spring');
    expect(typeof preset.stiffness).toBe('number');
  }
});

test('durations are ordered fast < base < slow', () => {
  expect(duration.fast).toBeLessThan(duration.base);
  expect(duration.base).toBeLessThan(duration.slow);
});

test('fadeRise enters from below and fades in', () => {
  expect(fadeRise.initial).toEqual({ opacity: 0, y: 8 });
  expect(fadeRise.animate).toEqual({ opacity: 1, y: 0 });
});
```

- [ ] **Step 3: Run the test**

Run: `npm test -- motion.test`
Expected: FAIL — `./motion` does not exist.

- [ ] **Step 4: Create the motion module**

`frontend/src/design/motion.ts`:

```ts
import type { Transition } from 'motion/react';

/** Spring presets — the dashboard's entire motion vocabulary. */
export const spring = {
  /** Calm; for layout shifts and large surfaces. */
  smooth: { type: 'spring', stiffness: 210, damping: 30, mass: 0.9 },
  /** Quick and tactile; for hover, press, and small controls. */
  snappy: { type: 'spring', stiffness: 440, damping: 34 },
  /** Soft landing; for elements entering the screen. */
  gentle: { type: 'spring', stiffness: 150, damping: 26 },
} satisfies Record<string, Transition>;

export const duration = { fast: 0.14, base: 0.26, slow: 0.5 } as const;

/** Easing for non-spring tweens (opacity, path morphs). */
export const easeOutExpo = [0.16, 1, 0.3, 1] as const;

/** Standard enter animation for cards and panels. */
export const fadeRise = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
} as const;
```

- [ ] **Step 5: Write the failing test for the reduced-motion hooks**

`frontend/src/lib/useReducedMotion.test.tsx`:

```tsx
import { renderHook } from '@testing-library/react';
import { useReducedMotion, useChartAnimationMs } from './useReducedMotion';

test('useReducedMotion returns a boolean', () => {
  const { result } = renderHook(() => useReducedMotion());
  expect(typeof result.current).toBe('boolean');
});

test('useChartAnimationMs returns the base duration when motion is allowed', () => {
  const { result } = renderHook(() => useChartAnimationMs(400));
  expect(result.current).toBe(400);
});
```

- [ ] **Step 6: Run the test**

Run: `npm test -- useReducedMotion`
Expected: FAIL — `./useReducedMotion` does not exist.

- [ ] **Step 7: Create the reduced-motion hooks**

`frontend/src/lib/useReducedMotion.ts`:

```ts
import { useReducedMotion as useMotionReducedMotion } from 'motion/react';

/** True when the user has requested reduced motion. */
export function useReducedMotion(): boolean {
  return useMotionReducedMotion() ?? false;
}

/**
 * Duration (ms) for D3-driven chart animations — `MotionConfig` does not
 * cover D3 transitions, so chart code reads this directly. 0 when reduced
 * motion is on.
 */
export function useChartAnimationMs(base = 450): number {
  return useReducedMotion() ? 0 : base;
}
```

- [ ] **Step 8: Wrap the app in `MotionConfig`**

`frontend/src/App.tsx` (replace the whole file):

```tsx
import { MotionConfig } from 'motion/react';
import { spring } from './design/motion';

export default function App() {
  return (
    <MotionConfig reducedMotion="user" transition={spring.smooth}>
      <div>News &amp; Markets Dashboard</div>
    </MotionConfig>
  );
}
```

- [ ] **Step 9: Run the tests**

Run: `npm test -- motion useReducedMotion App`
Expected: PASS (motion: 3, useReducedMotion: 2, App: 1).

- [ ] **Step 10: Commit**

```bash
git add frontend/src/design/motion.ts frontend/src/design/motion.test.ts \
  frontend/src/lib/useReducedMotion.ts frontend/src/lib/useReducedMotion.test.tsx \
  frontend/src/test/setup.ts frontend/src/App.tsx
git commit -m "feat(frontend): motion system with spring presets and reduced-motion hooks"
```

---

## Task 4: Formatters

**Files:**
- Create: `frontend/src/lib/format.ts`
- Test: `frontend/src/lib/format.test.ts`

- [ ] **Step 1: Write the failing test**

`frontend/src/lib/format.test.ts`:

```ts
import {
  trendOf, formatPrice, formatPercent, formatChange,
  formatCompact, formatDay, formatFullDate, formatUpdated,
} from './format';

test('trendOf classifies signed numbers', () => {
  expect(trendOf(1.2)).toBe('up');
  expect(trendOf(-0.3)).toBe('down');
  expect(trendOf(0)).toBe('flat');
});

test('formatPrice renders USD with two decimals', () => {
  expect(formatPrice(1234.5)).toBe('$1,234.50');
  expect(formatPrice(9.1)).toBe('$9.10');
});

test('formatPercent signs positives and formats to two decimals', () => {
  expect(formatPercent(1.234)).toBe('+1.23%');
  expect(formatPercent(-0.5)).toBe('-0.50%');
  expect(formatPercent(2.5, { sign: false })).toBe('2.50%');
});

test('formatChange signs the raw number', () => {
  expect(formatChange(1.8)).toBe('+1.80');
  expect(formatChange(-2)).toBe('-2.00');
});

test('formatCompact abbreviates large numbers and uses B for billions', () => {
  expect(formatCompact(3.42e12)).toBe('3.42T');
  expect(formatCompact(3.24e11)).toBe('324B');
  expect(formatCompact(null)).toBe('—');
});

test('formatDay and formatFullDate render UTC dates without TZ drift', () => {
  expect(formatDay('2026-05-20')).toBe('May 20');
  expect(formatFullDate('2026-05-20')).toBe('May 20, 2026');
});

test('formatUpdated produces an "Updated <time>" label', () => {
  expect(formatUpdated('2026-05-20T20:00:00+00:00')).toMatch(
    /^Updated \d{1,2}:\d{2} (AM|PM)$/,
  );
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- format.test`
Expected: FAIL — `./format` does not exist.

- [ ] **Step 3: Create the formatters**

`frontend/src/lib/format.ts`:

```ts
import { format } from 'd3-format';
import { utcFormat, timeFormat } from 'd3-time-format';

const compact = format('.3~s');
const utcDay = utcFormat('%b %-d');
const utcDayYear = utcFormat('%b %-d, %Y');
const localTime = timeFormat('%-I:%M %p');

export type Trend = 'up' | 'down' | 'flat';

/** Classify a signed number into a market trend direction. */
export function trendOf(n: number): Trend {
  if (n > 0) return 'up';
  if (n < 0) return 'down';
  return 'flat';
}

/** "$1,234.50" — USD, always two decimals. */
export function formatPrice(n: number): string {
  return n.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** "+1.23%" / "-0.50%". Input is already a percent number. */
export function formatPercent(n: number, opts: { sign?: boolean } = {}): string {
  const sign = opts.sign !== false && n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

/** "+1.80" / "-2.00" — signed plain number, two decimals. */
export function formatChange(n: number): string {
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}`;
}

/** Large numbers as "3.42T", "324B", "12.0M"; "—" for null/non-finite. */
export function formatCompact(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return '—';
  return compact(n).replace('G', 'B');
}

/** "May 20" — formats a date-only or ISO string in UTC (no TZ drift). */
export function formatDay(iso: string): string {
  return utcDay(new Date(iso));
}

/** "May 20, 2026" — formats a date-only or ISO string in UTC. */
export function formatFullDate(iso: string): string {
  return utcDayYear(new Date(iso));
}

/** "Updated 3:45 PM" — local time, for `updated_at` datetimes. */
export function formatUpdated(iso: string): string {
  return `Updated ${localTime(new Date(iso))}`;
}
```

- [ ] **Step 4: Run the test**

Run: `npm test -- format.test`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/format.ts frontend/src/lib/format.test.ts
git commit -m "feat(frontend): number, percent, and date formatters"
```

---

## Task 5: API types and HTTP client

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`
- Test: `frontend/src/lib/api.test.ts`

- [ ] **Step 1: Create the API types**

`frontend/src/lib/types.ts`:

```ts
/** TypeScript mirrors of the Phase 1a backend response shapes. */

export interface Bar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Quote {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  as_of: string;
}

export interface WatchlistQuote extends Quote {
  sparkline: number[];
}

export interface Fundamentals {
  symbol: string;
  name: string;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  pe_ratio: number | null;
  price_to_book: number | null;
  dividend_yield: number | null;
  week52_high: number | null;
  week52_low: number | null;
  beta: number | null;
}

export interface SectorChange {
  symbol: string;
  name: string;
  change_pct: number;
}

export interface Breadth {
  advancers: number;
  decliners: number;
  unchanged: number;
  advance_decline_ratio: number;
}

export interface OverviewResponse {
  watchlist: WatchlistQuote[];
  indices: Quote[];
  sectors: SectorChange[];
  breadth: Breadth;
  updated_at: string;
}

export interface Technicals {
  sma_20: (number | null)[];
  sma_50: (number | null)[];
  sma_200: (number | null)[];
}

export interface InstrumentStats {
  momentum_1m: number;
  momentum_3m: number;
  momentum_6m: number;
  volatility_30d: number;
  week52_high: number | null;
  week52_low: number | null;
}

export interface InstrumentResponse {
  symbol: string;
  profile: Fundamentals;
  bars: Bar[];
  technicals: Technicals;
  stats: InstrumentStats;
  updated_at: string;
}
```

- [ ] **Step 2: Write the failing test**

`frontend/src/lib/api.test.ts`:

```ts
import { afterEach, vi } from 'vitest';
import { apiFetch, setAuthToken, api } from './api';

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: 'Error',
    json: async () => body,
  } as Response);
}

afterEach(() => {
  setAuthToken(null);
  vi.restoreAllMocks();
});

test('apiFetch parses JSON on a successful response', async () => {
  globalThis.fetch = mockFetch(200, { status: 'ok' });
  await expect(apiFetch('/health')).resolves.toEqual({ status: 'ok' });
});

test('apiFetch attaches a bearer token when one is set', async () => {
  const f = mockFetch(200, {});
  globalThis.fetch = f;
  setAuthToken('secret-token');
  await apiFetch('/api/finance/overview');
  const headers = new Headers((f.mock.calls[0][1] as RequestInit).headers);
  expect(headers.get('Authorization')).toBe('Bearer secret-token');
});

test('apiFetch throws an ApiError carrying status and detail', async () => {
  globalThis.fetch = mockFetch(404, { detail: 'No data for ZZZZ' });
  await expect(apiFetch('/api/finance/instrument/ZZZZ')).rejects.toMatchObject({
    status: 404,
    message: 'No data for ZZZZ',
  });
});

test('api.instrument URL-encodes symbols with special characters', async () => {
  const f = mockFetch(200, {});
  globalThis.fetch = f;
  await api.instrument('^GSPC');
  expect(f.mock.calls[0][0]).toContain('/api/finance/instrument/%5EGSPC');
});
```

- [ ] **Step 3: Run the test**

Run: `npm test -- api.test`
Expected: FAIL — `./api` does not exist.

- [ ] **Step 4: Create the API client**

`frontend/src/lib/api.ts`:

```ts
import type {
  InstrumentResponse,
  OverviewResponse,
} from './types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

/** Error thrown for any non-2xx response, carrying the HTTP status. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

let authToken: string | null = null;

/** Set (or clear) the bearer token attached to every authed request. */
export function setAuthToken(token: string | null): void {
  authToken = token;
}

/** Fetch a JSON endpoint; throws ApiError on failure. */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set('Content-Type', 'application/json');
  if (authToken) headers.set('Authorization', `Bearer ${authToken}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body?.detail) detail = body.detail;
    } catch {
      // response had no JSON body — keep the status text
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Typed endpoint functions for the dashboard API. */
export const api = {
  authStatus: () => apiFetch<{ auth_enabled: boolean }>('/api/auth/status'),

  login: (password: string) =>
    apiFetch<{ token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    }),

  overview: () => apiFetch<OverviewResponse>('/api/finance/overview'),

  instrument: (symbol: string) =>
    apiFetch<InstrumentResponse>(
      `/api/finance/instrument/${encodeURIComponent(symbol)}`,
    ),

  addWatchlist: (symbol: string) =>
    apiFetch<{ symbols: string[] }>('/api/watchlist', {
      method: 'POST',
      body: JSON.stringify({ symbol }),
    }),

  removeWatchlist: (symbol: string) =>
    apiFetch<{ symbols: string[] }>(
      `/api/watchlist/${encodeURIComponent(symbol)}`,
      { method: 'DELETE' },
    ),
};
```

- [ ] **Step 5: Run the test**

Run: `npm test -- api.test`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/lib/api.test.ts
git commit -m "feat(frontend): API types and HTTP client"
```

---

## Task 6: Query client, auth context, and test helpers

**Files:**
- Create: `frontend/src/lib/queryClient.ts`
- Create: `frontend/src/auth/AuthContext.tsx`
- Create: `frontend/src/test/utils.tsx`
- Test: `frontend/src/auth/AuthContext.test.tsx`

- [ ] **Step 1: Create the TanStack Query client**

`frontend/src/lib/queryClient.ts`:

```ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

- [ ] **Step 2: Create the shared test helper**

`frontend/src/test/utils.tsx`:

```tsx
import type { ReactElement, ReactNode } from 'react';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';

/** A fresh QueryClient with retries off — isolates each test. */
export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

interface RenderOptions {
  /** Initial URL. */
  route?: string;
  /** Route pattern, e.g. "/finance/:symbol" when the UI reads params. */
  path?: string;
}

/**
 * Render `ui` inside a data router + QueryClientProvider. A data router
 * (not <MemoryRouter>) is required for `<Link viewTransition>` and
 * `useViewTransitionState` to work in tests.
 */
export function renderWithProviders(
  ui: ReactElement,
  { route = '/', path = '*' }: RenderOptions = {},
) {
  const qc = makeQueryClient();
  const router = createMemoryRouter(
    [
      {
        path,
        element: <QueryClientProvider client={qc}>{ui}</QueryClientProvider>,
      },
    ],
    { initialEntries: [route] },
  );
  return { qc, router, ...render(<RouterProvider router={router} />) };
}

/** Convenience wrapper component for `renderHook`. */
export function QueryWrapper({ children }: { children: ReactNode }) {
  const qc = makeQueryClient();
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}
```

- [ ] **Step 3: Write the failing test**

`frontend/src/auth/AuthContext.test.tsx`:

```tsx
import { beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from './AuthContext';

vi.mock('../lib/api', () => ({
  setAuthToken: vi.fn(),
  api: {
    authStatus: vi.fn().mockResolvedValue({ auth_enabled: true }),
    login: vi.fn().mockResolvedValue({ token: 'tok-123' }),
  },
}));

function Probe() {
  const { ready, authed, login } = useAuth();
  return (
    <div>
      <span>ready:{String(ready)}</span>
      <span>authed:{String(authed)}</span>
      <button onClick={() => void login('pw')}>do-login</button>
    </div>
  );
}

beforeEach(() => localStorage.clear());

test('reports auth required and unauthed before login', async () => {
  render(<AuthProvider><Probe /></AuthProvider>);
  await waitFor(() => expect(screen.getByText('ready:true')).toBeInTheDocument());
  expect(screen.getByText('authed:false')).toBeInTheDocument();
});

test('login stores a token and flips to authed', async () => {
  render(<AuthProvider><Probe /></AuthProvider>);
  await waitFor(() => expect(screen.getByText('ready:true')).toBeInTheDocument());
  await userEvent.click(screen.getByText('do-login'));
  await waitFor(() => expect(screen.getByText('authed:true')).toBeInTheDocument());
  expect(localStorage.getItem('nmd.token')).toBe('tok-123');
});
```

- [ ] **Step 4: Run the test**

Run: `npm test -- AuthContext`
Expected: FAIL — `./AuthContext` does not exist.

- [ ] **Step 5: Create the auth context**

`frontend/src/auth/AuthContext.tsx`:

```tsx
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import type { ReactNode } from 'react';
import { api, setAuthToken } from '../lib/api';

const STORAGE_KEY = 'nmd.token';

interface AuthState {
  /** True once `/api/auth/status` has been checked. */
  ready: boolean;
  /** True when the backend has a token configured. */
  authRequired: boolean;
  token: string | null;
  /** True when access is allowed (auth not required, or a token is held). */
  authed: boolean;
  login: (password: string) => Promise<void>;
  logout: () => void;
}

const AuthCtx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authRequired, setAuthRequired] = useState(false);
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(STORAGE_KEY),
  );

  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  useEffect(() => {
    api
      .authStatus()
      .then((s) => setAuthRequired(s.auth_enabled))
      .catch(() => setAuthRequired(false))
      .finally(() => setReady(true));
  }, []);

  const login = useCallback(async (password: string) => {
    const { token: fresh } = await api.login(password);
    localStorage.setItem(STORAGE_KEY, fresh);
    setToken(fresh);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
  }, []);

  const authed = !authRequired || token !== null;

  return (
    <AuthCtx.Provider
      value={{ ready, authRequired, token, authed, login, logout }}
    >
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
```

- [ ] **Step 6: Run the test**

Run: `npm test -- AuthContext`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/queryClient.ts frontend/src/auth/AuthContext.tsx \
  frontend/src/test/utils.tsx frontend/src/auth/AuthContext.test.tsx
git commit -m "feat(frontend): query client, auth context, and test helpers"
```

---

## Task 7: Login screen and auth gate

**Files:**
- Create: `frontend/src/auth/LoginScreen.tsx`
- Create: `frontend/src/auth/AuthGate.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx` (replace the whole file)
- Test: `frontend/src/auth/LoginScreen.test.tsx`, `frontend/src/auth/AuthGate.test.tsx`

- [ ] **Step 1: Write the failing test for the login screen**

`frontend/src/auth/LoginScreen.test.tsx`:

```tsx
import { vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoginScreen } from './LoginScreen';

const login = vi.fn();
vi.mock('./AuthContext', () => ({
  useAuth: () => ({ login }),
}));

test('submitting the form calls login with the password', async () => {
  login.mockResolvedValueOnce(undefined);
  render(<LoginScreen />);
  await userEvent.type(screen.getByLabelText('Password'), 'hunter2');
  await userEvent.click(screen.getByRole('button', { name: /enter/i }));
  expect(login).toHaveBeenCalledWith('hunter2');
});

test('shows an error message when login fails', async () => {
  login.mockRejectedValueOnce(new Error('bad'));
  render(<LoginScreen />);
  await userEvent.type(screen.getByLabelText('Password'), 'wrong');
  await userEvent.click(screen.getByRole('button', { name: /enter/i }));
  await waitFor(() =>
    expect(screen.getByText(/incorrect password/i)).toBeInTheDocument(),
  );
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- LoginScreen`
Expected: FAIL — `./LoginScreen` does not exist.

- [ ] **Step 3: Create the login screen**

`frontend/src/auth/LoginScreen.tsx`:

```tsx
import { useState } from 'react';
import type { FormEvent } from 'react';
import { motion } from 'motion/react';
import { useAuth } from './AuthContext';
import { spring } from '../design/motion';

export function LoginScreen() {
  const { login } = useAuth();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(password);
    } catch {
      setError('Incorrect password');
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-bg p-6">
      <motion.form
        onSubmit={onSubmit}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring.gentle}
        className="w-full max-w-sm rounded-lg border border-border bg-surface p-8"
      >
        <h1 className="font-mono text-xs tracking-widest text-ink-mute uppercase">
          News &amp; Markets
        </h1>
        <p className="mt-1 text-lg font-medium text-ink">Sign in</p>

        <input
          type="password"
          aria-label="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
          className="mt-6 w-full rounded-md border border-border bg-raised px-3 py-2
                     text-ink outline-none transition-colors focus:border-accent"
        />

        {error && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-2 text-sm text-down"
          >
            {error}
          </motion.p>
        )}

        <motion.button
          type="submit"
          disabled={busy}
          whileTap={{ scale: 0.97 }}
          className="mt-6 w-full rounded-md bg-accent py-2 font-medium text-bg
                     transition-opacity disabled:opacity-50"
        >
          {busy ? 'Signing in…' : 'Enter'}
        </motion.button>
      </motion.form>
    </div>
  );
}
```

- [ ] **Step 4: Write the failing test for the auth gate**

`frontend/src/auth/AuthGate.test.tsx`:

```tsx
import { vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AuthGate } from './AuthGate';

const state = {
  ready: true,
  authed: true,
};
vi.mock('./AuthContext', () => ({
  useAuth: () => state,
}));
vi.mock('./LoginScreen', () => ({
  LoginScreen: () => <div>login-screen</div>,
}));

test('renders children when authed', () => {
  state.ready = true;
  state.authed = true;
  render(<AuthGate><div>protected</div></AuthGate>);
  expect(screen.getByText('protected')).toBeInTheDocument();
});

test('renders the login screen when not authed', () => {
  state.ready = true;
  state.authed = false;
  render(<AuthGate><div>protected</div></AuthGate>);
  expect(screen.getByText('login-screen')).toBeInTheDocument();
});

test('renders a loader before the auth status is known', () => {
  state.ready = false;
  state.authed = false;
  render(<AuthGate><div>protected</div></AuthGate>);
  expect(screen.getByRole('status')).toBeInTheDocument();
});
```

- [ ] **Step 5: Run the test**

Run: `npm test -- AuthGate`
Expected: FAIL — `./AuthGate` does not exist.

- [ ] **Step 6: Create the auth gate**

`frontend/src/auth/AuthGate.tsx`:

```tsx
import type { ReactNode } from 'react';
import { useAuth } from './AuthContext';
import { LoginScreen } from './LoginScreen';

function FullScreenLoader() {
  return (
    <div
      role="status"
      aria-label="Loading"
      className="flex min-h-full items-center justify-center bg-bg"
    >
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-border
                      border-t-accent" />
    </div>
  );
}

export function AuthGate({ children }: { children: ReactNode }) {
  const { ready, authed } = useAuth();
  if (!ready) return <FullScreenLoader />;
  if (!authed) return <LoginScreen />;
  return <>{children}</>;
}
```

- [ ] **Step 7: Wire the providers into `App.tsx`**

`frontend/src/App.tsx` (replace the whole file):

```tsx
import { QueryClientProvider } from '@tanstack/react-query';
import { MotionConfig } from 'motion/react';
import { AuthProvider } from './auth/AuthContext';
import { AuthGate } from './auth/AuthGate';
import { queryClient } from './lib/queryClient';
import { spring } from './design/motion';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user" transition={spring.smooth}>
        <AuthProvider>
          <AuthGate>
            <div>News &amp; Markets Dashboard</div>
          </AuthGate>
        </AuthProvider>
      </MotionConfig>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 8: Update the App test for the async auth gate**

`App` now renders the auth gate, which is briefly in a loading state. Replace
`frontend/src/App.test.tsx` (whole file):

```tsx
import { vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

vi.mock('./lib/api', () => ({
  setAuthToken: vi.fn(),
  api: {
    authStatus: vi.fn().mockResolvedValue({ auth_enabled: false }),
  },
}));

test('renders the protected content once the auth status resolves', async () => {
  render(<App />);
  await waitFor(() =>
    expect(
      screen.getByText('News & Markets Dashboard'),
    ).toBeInTheDocument(),
  );
});
```

- [ ] **Step 9: Run the tests**

Run: `npm test -- LoginScreen AuthGate App`
Expected: PASS (LoginScreen: 2, AuthGate: 3, App: 1).

- [ ] **Step 10: Commit**

```bash
git add frontend/src/auth/LoginScreen.tsx frontend/src/auth/LoginScreen.test.tsx \
  frontend/src/auth/AuthGate.tsx frontend/src/auth/AuthGate.test.tsx \
  frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat(frontend): login screen and auth gate"
```

---

## Task 8: Chart foundation — dimensions, frame, axis, colors

**Files:**
- Create: `frontend/src/charts/useChartDimensions.ts`
- Create: `frontend/src/charts/ChartFrame.tsx`
- Create: `frontend/src/charts/Axis.tsx`
- Create: `frontend/src/charts/colors.ts`
- Modify: `frontend/src/test/setup.ts` (add `ResizeObserver` mock)
- Test: `frontend/src/charts/useChartDimensions.test.tsx`, `frontend/src/charts/ChartFrame.test.tsx`, `frontend/src/charts/Axis.test.tsx`, `frontend/src/charts/colors.test.ts`

- [ ] **Step 1: Add a `ResizeObserver` mock to the test setup**

`frontend/src/test/setup.ts` (replace the whole file):

```ts
import '@testing-library/jest-dom/vitest';

// jsdom does not implement matchMedia; motion's reduced-motion hook needs it.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }),
});

// jsdom does not implement ResizeObserver; charts observe their container.
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver =
  ResizeObserverMock as unknown as typeof ResizeObserver;
```

- [ ] **Step 2: Write the failing test for `useChartDimensions`**

`frontend/src/charts/useChartDimensions.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { useChartDimensions } from './useChartDimensions';

function Probe() {
  const [ref, dims] = useChartDimensions<HTMLDivElement>({
    width: 300,
    height: 150,
  });
  return <div ref={ref}>{`${dims.width}x${dims.height}`}</div>;
}

test('returns the fallback dimensions when the element is unmeasured', () => {
  render(<Probe />);
  expect(screen.getByText('300x150')).toBeInTheDocument();
});
```

- [ ] **Step 3: Run the test**

Run: `npm test -- useChartDimensions`
Expected: FAIL — `./useChartDimensions` does not exist.

- [ ] **Step 4: Create `useChartDimensions`**

`frontend/src/charts/useChartDimensions.ts`:

```ts
import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';

export interface Dimensions {
  width: number;
  height: number;
}

/**
 * Observe an element's size with a ResizeObserver. Returns a ref to attach
 * and the live dimensions, starting from `fallback` until first measured.
 */
export function useChartDimensions<T extends Element>(
  fallback: Dimensions = { width: 640, height: 320 },
): [RefObject<T | null>, Dimensions] {
  const ref = useRef<T>(null);
  const [dims, setDims] = useState<Dimensions>(fallback);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const box = entries[0]?.contentRect;
      if (box && box.width > 0 && box.height > 0) {
        setDims({ width: box.width, height: box.height });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return [ref, dims];
}
```

- [ ] **Step 5: Write the failing test for `ChartFrame`**

`frontend/src/charts/ChartFrame.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { ChartFrame } from './ChartFrame';

test('renders a sized svg and gives children the inner dimensions', () => {
  let inner = { width: 0, height: 0 };
  const { container } = render(
    <ChartFrame
      width={200}
      height={100}
      margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
    >
      {(d) => {
        inner = d;
        return <circle data-testid="mark" />;
      }}
    </ChartFrame>,
  );
  const svg = container.querySelector('svg')!;
  expect(svg.getAttribute('viewBox')).toBe('0 0 200 100');
  expect(inner).toEqual({ width: 180, height: 80 });
  expect(container.querySelector('[data-testid="mark"]')).not.toBeNull();
});
```

- [ ] **Step 6: Run the test**

Run: `npm test -- ChartFrame`
Expected: FAIL — `./ChartFrame` does not exist.

- [ ] **Step 7: Create `ChartFrame`**

`frontend/src/charts/ChartFrame.tsx`:

```tsx
import type { ReactNode } from 'react';

export interface Margin {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

const DEFAULT_MARGIN: Margin = { top: 8, right: 8, bottom: 24, left: 40 };

interface ChartFrameProps {
  width: number;
  height: number;
  margin?: Partial<Margin>;
  /** Render-prop receiving the inner plotting area dimensions. */
  children: (inner: { width: number; height: number }) => ReactNode;
  className?: string;
  label?: string;
}

/** Responsive SVG with the standard D3 margin convention. */
export function ChartFrame({
  width,
  height,
  margin,
  children,
  className,
  label,
}: ChartFrameProps) {
  const m = { ...DEFAULT_MARGIN, ...margin };
  const innerWidth = Math.max(0, width - m.left - m.right);
  const innerHeight = Math.max(0, height - m.top - m.bottom);
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={label}
      className={className}
    >
      <g transform={`translate(${m.left},${m.top})`}>
        {children({ width: innerWidth, height: innerHeight })}
      </g>
    </svg>
  );
}
```

- [ ] **Step 8: Write the failing test for `Axis`**

`frontend/src/charts/Axis.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { Axis } from './Axis';

test('renders one label per tick', () => {
  const { container } = render(
    <svg>
      <Axis
        orientation="left"
        ticks={[
          { value: 0, offset: 100, label: '0' },
          { value: 50, offset: 50, label: '50' },
          { value: 100, offset: 0, label: '100' },
        ]}
      />
    </svg>,
  );
  const texts = container.querySelectorAll('text');
  expect(texts).toHaveLength(3);
  expect(texts[1].textContent).toBe('50');
});
```

- [ ] **Step 9: Run the test**

Run: `npm test -- Axis`
Expected: FAIL — `./Axis` does not exist.

- [ ] **Step 10: Create `Axis`**

`frontend/src/charts/Axis.tsx`:

```tsx
import { tokens } from '../design/tokens';

export interface AxisTick {
  value: number;
  offset: number;
  label: string;
}

interface AxisProps {
  orientation: 'bottom' | 'left';
  /** Precomputed ticks — keeps the Axis decoupled from any specific scale. */
  ticks: AxisTick[];
  className?: string;
}

export function Axis({ orientation, ticks, className }: AxisProps) {
  const isBottom = orientation === 'bottom';
  return (
    <g className={className} aria-hidden="true">
      {ticks.map((t) => (
        <text
          key={t.value}
          transform={
            isBottom
              ? `translate(${t.offset}, 16)`
              : `translate(-8, ${t.offset})`
          }
          textAnchor={isBottom ? 'middle' : 'end'}
          dominantBaseline="middle"
          fontSize={10}
          fontFamily={tokens.font.mono}
          fill={tokens.color.inkMute}
        >
          {t.label}
        </text>
      ))}
    </g>
  );
}
```

- [ ] **Step 11: Write the failing test for `colors`**

`frontend/src/charts/colors.test.ts`:

```ts
import { heatColor, trendColor, smaColor } from './colors';
import { tokens } from '../design/tokens';

test('heatColor maps strong gains to the up color and losses to down', () => {
  expect(heatColor(2)).toBe(tokens.color.up);
  expect(heatColor(-2)).toBe(tokens.color.down);
});

test('trendColor returns semantic colors for signed values', () => {
  expect(trendColor(1)).toBe(tokens.color.up);
  expect(trendColor(-1)).toBe(tokens.color.down);
  expect(trendColor(0)).toBe(tokens.color.flat);
});

test('smaColor has a distinct color per moving-average window', () => {
  expect(new Set([smaColor[20], smaColor[50], smaColor[200]]).size).toBe(3);
});
```

- [ ] **Step 12: Run the test**

Run: `npm test -- colors`
Expected: FAIL — `./colors` does not exist.

- [ ] **Step 13: Create `colors`**

`frontend/src/charts/colors.ts`:

```ts
import { scaleLinear } from 'd3-scale';
import { tokens } from '../design/tokens';

const heat = scaleLinear<string>()
  .domain([-2, 0, 2])
  .range([tokens.color.down, tokens.color.raised, tokens.color.up])
  .clamp(true);

/** Diverging heat color for a percent change (down ↔ flat ↔ up). */
export function heatColor(changePct: number): string {
  return heat(changePct);
}

/** Semantic color for a signed value. */
export function trendColor(n: number): string {
  if (n > 0) return tokens.color.up;
  if (n < 0) return tokens.color.down;
  return tokens.color.flat;
}

/** Stroke colors for the moving-average overlays on the candlestick chart. */
export const smaColor = {
  20: tokens.color.accent,
  50: '#d2a44e',
  200: tokens.color.inkSoft,
} as const;
```

- [ ] **Step 14: Run all chart-foundation tests**

Run: `npm test -- useChartDimensions ChartFrame Axis colors`
Expected: PASS (useChartDimensions: 1, ChartFrame: 1, Axis: 1, colors: 3).

- [ ] **Step 15: Commit**

```bash
git add frontend/src/charts/useChartDimensions.ts frontend/src/charts/useChartDimensions.test.tsx \
  frontend/src/charts/ChartFrame.tsx frontend/src/charts/ChartFrame.test.tsx \
  frontend/src/charts/Axis.tsx frontend/src/charts/Axis.test.tsx \
  frontend/src/charts/colors.ts frontend/src/charts/colors.test.ts \
  frontend/src/test/setup.ts
git commit -m "feat(frontend): chart foundation — dimensions, frame, axis, colors"
```

---

## Task 9: Sparkline chart

**Files:**
- Create: `frontend/src/charts/Sparkline.tsx`
- Test: `frontend/src/charts/Sparkline.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/charts/Sparkline.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { Sparkline } from './Sparkline';

test('renders a line path, an area fill, and a gradient', () => {
  const { container } = render(
    <Sparkline values={[10, 12, 11, 14, 13, 16]} />,
  );
  expect(container.querySelectorAll('path')).toHaveLength(2);
  expect(container.querySelector('linearGradient')).not.toBeNull();
  const line = container.querySelectorAll('path')[1];
  expect(line.getAttribute('d')).toMatch(/^M/);
});

test('renders an empty svg without crashing for too-few points', () => {
  const { container } = render(<Sparkline values={[10]} />);
  expect(container.querySelector('svg')).not.toBeNull();
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- Sparkline`
Expected: FAIL — `./Sparkline` does not exist.

- [ ] **Step 3: Create the Sparkline**

`frontend/src/charts/Sparkline.tsx`:

```tsx
import { useId, useMemo } from 'react';
import { area, curveMonotoneX, line } from 'd3-shape';
import { scaleLinear } from 'd3-scale';
import { extent } from 'd3-array';
import { trendColor } from './colors';

interface SparklineProps {
  values: number[];
  width?: number;
  height?: number;
}

/** A compact, axis-free trend line with a soft gradient fill. */
export function Sparkline({ values, width = 96, height = 28 }: SparklineProps) {
  const rawId = useId();
  const gradientId = `spark-${rawId.replace(/:/g, '')}`;

  const { linePath, areaPath, color } = useMemo(() => {
    if (values.length < 2) {
      return { linePath: '', areaPath: '', color: trendColor(0) };
    }
    const [min, max] = extent(values) as [number, number];
    const x = scaleLinear().domain([0, values.length - 1]).range([1, width - 1]);
    const y = scaleLinear().domain([min, max]).range([height - 2, 2]);

    const l = line<number>()
      .x((_, i) => x(i))
      .y((d) => y(d))
      .curve(curveMonotoneX);
    const a = area<number>()
      .x((_, i) => x(i))
      .y0(height)
      .y1((d) => y(d))
      .curve(curveMonotoneX);

    return {
      linePath: l(values) ?? '',
      areaPath: a(values) ?? '',
      color: trendColor(values[values.length - 1] - values[0]),
    };
  }, [values, width, height]);

  return (
    <svg
      width={width}
      height={height}
      role="img"
      aria-label="Trend sparkline"
      className="overflow-visible"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.28} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradientId})`} />
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
```

- [ ] **Step 4: Run the test**

Run: `npm test -- Sparkline`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/charts/Sparkline.tsx frontend/src/charts/Sparkline.test.tsx
git commit -m "feat(frontend): sparkline chart"
```

---

## Task 10: App shell — app bar, briefing ribbon, quadrant grid, panel

**Files:**
- Create: `frontend/src/components/Panel.tsx`, `frontend/src/components/ComingSoonPanel.tsx`, `frontend/src/components/PanelSkeleton.tsx`, `frontend/src/components/QuadrantGrid.tsx`, `frontend/src/components/AppBar.tsx`, `frontend/src/components/BriefingRibbon.tsx`, `frontend/src/components/AppShell.tsx`
- Test: `frontend/src/components/shell.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/components/shell.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { Panel } from './Panel';
import { ComingSoonPanel } from './ComingSoonPanel';
import { PanelSkeleton } from './PanelSkeleton';
import { QuadrantGrid } from './QuadrantGrid';
import { AppShell } from './AppShell';

test('Panel renders its title, action, and children', () => {
  render(
    <Panel title="Finance" icon="💹" action={<span>act</span>}>
      <div>body</div>
    </Panel>,
  );
  expect(screen.getByText('Finance')).toBeInTheDocument();
  expect(screen.getByText('act')).toBeInTheDocument();
  expect(screen.getByText('body')).toBeInTheDocument();
});

test('ComingSoonPanel names the domain and its arrival phase', () => {
  render(<ComingSoonPanel title="News" icon="📰" phase="Phase 3" />);
  expect(screen.getByText('News')).toBeInTheDocument();
  expect(screen.getByText(/Phase 3/)).toBeInTheDocument();
});

test('PanelSkeleton exposes a loading status', () => {
  render(<PanelSkeleton rows={3} />);
  expect(screen.getByRole('status')).toBeInTheDocument();
});

test('QuadrantGrid renders all four domain slots', () => {
  render(
    <QuadrantGrid
      news={<div>N</div>}
      politics={<div>P</div>}
      economics={<div>E</div>}
      finance={<div>F</div>}
    />,
  );
  for (const t of ['N', 'P', 'E', 'F']) {
    expect(screen.getByText(t)).toBeInTheDocument();
  }
});

test('AppShell renders the app bar, briefing ribbon, and children', () => {
  render(<AppShell><div>shell-body</div></AppShell>);
  expect(screen.getByText('NMD')).toBeInTheDocument();
  expect(screen.getByText(/Daily Briefing/i)).toBeInTheDocument();
  expect(screen.getByText('shell-body')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- shell.test`
Expected: FAIL — the component modules do not exist.

- [ ] **Step 3: Create `Panel`**

`frontend/src/components/Panel.tsx`:

```tsx
import type { ReactNode } from 'react';
import { motion } from 'motion/react';
import { clsx } from 'clsx';
import { fadeRise, spring } from '../design/motion';

interface PanelProps {
  title: string;
  icon: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** The shared frame for every domain panel — header bar plus body. */
export function Panel({ title, icon, action, children, className }: PanelProps) {
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
          <h2 className="font-mono text-xs tracking-widest text-ink-soft uppercase">
            {title}
          </h2>
        </div>
        {action}
      </header>
      <div className="flex-1 p-4">{children}</div>
    </motion.section>
  );
}
```

- [ ] **Step 4: Create `ComingSoonPanel`**

`frontend/src/components/ComingSoonPanel.tsx`:

```tsx
import { Panel } from './Panel';

interface ComingSoonPanelProps {
  title: string;
  icon: string;
  phase: string;
}

/** Placeholder panel for domains not yet built (News, Politics, Economics). */
export function ComingSoonPanel({ title, icon, phase }: ComingSoonPanelProps) {
  return (
    <Panel title={title} icon={icon}>
      <div className="flex min-h-40 flex-col items-center justify-center gap-1
                      text-center">
        <p className="text-sm text-ink-soft">Arriving in {phase}</p>
        <p className="text-xs text-ink-mute">
          This domain comes online in a later build phase.
        </p>
      </div>
    </Panel>
  );
}
```

- [ ] **Step 5: Create `PanelSkeleton`**

`frontend/src/components/PanelSkeleton.tsx`:

```tsx
interface PanelSkeletonProps {
  rows?: number;
}

/** Shimmer placeholder shown while a panel's data loads. */
export function PanelSkeleton({ rows = 4 }: PanelSkeletonProps) {
  return (
    <div role="status" aria-label="Loading" className="flex flex-col gap-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-6 animate-pulse rounded-md bg-raised" />
      ))}
    </div>
  );
}
```

- [ ] **Step 6: Create `QuadrantGrid`**

`frontend/src/components/QuadrantGrid.tsx`:

```tsx
import type { ReactNode } from 'react';

interface QuadrantGridProps {
  news: ReactNode;
  politics: ReactNode;
  economics: ReactNode;
  finance: ReactNode;
}

/** The 2×2 domain grid; collapses to a single column on small screens. */
export function QuadrantGrid({
  news,
  politics,
  economics,
  finance,
}: QuadrantGridProps) {
  return (
    <div className="grid flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-2">
      {news}
      {politics}
      {economics}
      {finance}
    </div>
  );
}
```

- [ ] **Step 7: Create `AppBar`**

`frontend/src/components/AppBar.tsx`:

```tsx
import { formatFullDate } from '../lib/format';

export function AppBar() {
  const today = formatFullDate(new Date().toISOString());
  return (
    <header className="flex items-center justify-between border-b border-border
                       bg-surface px-5 py-3">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-sm font-semibold tracking-widest text-ink">
          NMD
        </span>
        <span className="text-xs text-ink-mute">{today}</span>
      </div>
      <button
        type="button"
        className="rounded-md border border-border px-3 py-1.5 text-xs text-ink-soft
                   transition-colors hover:border-border-strong"
      >
        Search <kbd className="ml-1 text-ink-mute">⌘K</kbd>
      </button>
    </header>
  );
}
```

- [ ] **Step 8: Create `BriefingRibbon`**

`frontend/src/components/BriefingRibbon.tsx`:

```tsx
import { motion } from 'motion/react';
import { spring } from '../design/motion';

/** Full-width strip below the app bar. Placeholder until the Phase 5 AI layer. */
export function BriefingRibbon() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={spring.smooth}
      className="border-b border-border bg-surface px-5 py-3"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-mono text-[10px] tracking-widest text-accent uppercase">
          Daily Briefing
        </span>
        <p className="text-sm text-ink-soft">
          AI synthesis of the day's news, markets, and politics arrives in a
          later phase.
        </p>
      </div>
    </motion.div>
  );
}
```

- [ ] **Step 9: Create `AppShell`**

`frontend/src/components/AppShell.tsx`:

```tsx
import type { ReactNode } from 'react';
import { AppBar } from './AppBar';
import { BriefingRibbon } from './BriefingRibbon';

/** The persistent chrome: app bar + briefing ribbon, with routed content below. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-full flex-col bg-bg">
      <AppBar />
      <BriefingRibbon />
      {children}
    </div>
  );
}
```

- [ ] **Step 10: Run the test**

Run: `npm test -- shell.test`
Expected: PASS (5 tests).

- [ ] **Step 11: Commit**

```bash
git add frontend/src/components frontend/src/components/shell.test.tsx
git commit -m "feat(frontend): app shell — bar, ribbon, quadrant grid, panel"
```

---

## Task 11: Routing and the Home route

**Files:**
- Create: `frontend/src/routes/Home.tsx`, `frontend/src/routes/InstrumentRoute.tsx`, `frontend/src/router.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx` (replace the whole file)
- Test: `frontend/src/routes/Home.test.tsx`

> **Note:** in this task the Finance quadrant is also a `ComingSoonPanel` placeholder. Task 16 replaces it with the real `<FinancePanel />`.

- [ ] **Step 1: Create the Home route**

`frontend/src/routes/Home.tsx`:

```tsx
import { AppShell } from '../components/AppShell';
import { QuadrantGrid } from '../components/QuadrantGrid';
import { ComingSoonPanel } from '../components/ComingSoonPanel';

export function Home() {
  return (
    <AppShell>
      <QuadrantGrid
        news={<ComingSoonPanel title="News" icon="📰" phase="Phase 3" />}
        politics={<ComingSoonPanel title="Politics" icon="🏛" phase="Phase 4" />}
        economics={<ComingSoonPanel title="Economics" icon="📊" phase="Phase 2" />}
        finance={<ComingSoonPanel title="Finance" icon="💹" phase="this build" />}
      />
    </AppShell>
  );
}
```

- [ ] **Step 2: Create the instrument route stub**

`frontend/src/routes/InstrumentRoute.tsx`:

```tsx
import { useParams } from 'react-router-dom';

/** Placeholder — the full drill-down page is built in Task 19. */
export function InstrumentRoute() {
  const { symbol = '' } = useParams();
  return <div>Instrument: {symbol}</div>;
}
```

- [ ] **Step 3: Create the router**

`frontend/src/router.tsx`:

```tsx
import { createBrowserRouter } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { Home } from './routes/Home';
import { InstrumentRoute } from './routes/InstrumentRoute';

export const routes: RouteObject[] = [
  { path: '/', element: <Home /> },
  { path: '/finance/:symbol', element: <InstrumentRoute /> },
];

export const router = createBrowserRouter(routes);
```

- [ ] **Step 4: Wire the router into `App.tsx`**

`frontend/src/App.tsx` (replace the whole file):

```tsx
import { QueryClientProvider } from '@tanstack/react-query';
import { MotionConfig } from 'motion/react';
import { RouterProvider } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { AuthGate } from './auth/AuthGate';
import { queryClient } from './lib/queryClient';
import { router } from './router';
import { spring } from './design/motion';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user" transition={spring.smooth}>
        <AuthProvider>
          <AuthGate>
            <RouterProvider router={router} />
          </AuthGate>
        </AuthProvider>
      </MotionConfig>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 5: Write the failing test for Home**

`frontend/src/routes/Home.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { Home } from './Home';

test('renders the four-quadrant dashboard shell', () => {
  render(<Home />);
  expect(screen.getByText('NMD')).toBeInTheDocument();
  expect(screen.getByText('News')).toBeInTheDocument();
  expect(screen.getByText('Politics')).toBeInTheDocument();
  expect(screen.getByText('Economics')).toBeInTheDocument();
  expect(screen.getByText('Finance')).toBeInTheDocument();
});
```

- [ ] **Step 6: Replace the App test**

`frontend/src/App.test.tsx` (replace the whole file). The mock includes
`overview` because, after Task 16, `App` renders the data-backed Finance panel:

```tsx
import { vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

vi.mock('./lib/api', () => ({
  setAuthToken: vi.fn(),
  api: {
    authStatus: vi.fn().mockResolvedValue({ auth_enabled: false }),
    overview: vi.fn().mockResolvedValue({
      watchlist: [], indices: [], sectors: [],
      breadth: {
        advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0,
      },
      updated_at: '2026-05-20T20:00:00+00:00',
    }),
    addWatchlist: vi.fn(),
    removeWatchlist: vi.fn(),
  },
}));

test('renders the dashboard once the auth status resolves', async () => {
  render(<App />);
  await waitFor(() =>
    expect(screen.getByText('NMD')).toBeInTheDocument(),
  );
});
```

- [ ] **Step 7: Run the tests**

Run: `npm test -- Home.test App.test`
Expected: PASS (Home: 1, App: 1).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/routes frontend/src/router.tsx frontend/src/App.tsx \
  frontend/src/App.test.tsx
git commit -m "feat(frontend): routing and the four-quadrant Home route"
```

---

## Task 12: Finance data hooks

**Files:**
- Create: `frontend/src/finance/hooks.ts`
- Test: `frontend/src/finance/hooks.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/finance/hooks.test.tsx`:

```tsx
import { vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryWrapper } from '../test/utils';
import { useOverview, useInstrument } from './hooks';

vi.mock('../lib/api', () => ({
  api: {
    overview: vi.fn().mockResolvedValue({
      watchlist: [], indices: [], sectors: [],
      breadth: { advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0 },
      updated_at: '2026-05-20T20:00:00+00:00',
    }),
    instrument: vi.fn().mockResolvedValue({ symbol: 'AAPL' }),
  },
}));

test('useOverview fetches the finance overview', async () => {
  const { result } = renderHook(() => useOverview(), { wrapper: QueryWrapper });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.updated_at).toBe('2026-05-20T20:00:00+00:00');
});

test('useInstrument fetches the requested symbol', async () => {
  const { result } = renderHook(() => useInstrument('AAPL'), {
    wrapper: QueryWrapper,
  });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(result.current.data?.symbol).toBe('AAPL');
});

test('useInstrument stays idle for an empty symbol', () => {
  const { result } = renderHook(() => useInstrument(''), {
    wrapper: QueryWrapper,
  });
  expect(result.current.fetchStatus).toBe('idle');
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- hooks.test`
Expected: FAIL — `./hooks` does not exist.

- [ ] **Step 3: Create the finance hooks**

`frontend/src/finance/hooks.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

/** The Finance overview — refetched every 60s to stay live. */
export function useOverview() {
  return useQuery({
    queryKey: ['overview'],
    queryFn: api.overview,
    refetchInterval: 60_000,
  });
}

/** A single instrument's drill-down data. Disabled for an empty symbol. */
export function useInstrument(symbol: string) {
  return useQuery({
    queryKey: ['instrument', symbol],
    queryFn: () => api.instrument(symbol),
    enabled: symbol.length > 0,
  });
}

/**
 * Add/remove watchlist mutations. The watchlist is part of the overview
 * response, so both invalidate the overview query on success.
 */
export function useWatchlistMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ['overview'] });
  const add = useMutation({ mutationFn: api.addWatchlist, onSuccess: invalidate });
  const remove = useMutation({
    mutationFn: api.removeWatchlist,
    onSuccess: invalidate,
  });
  return { add, remove };
}
```

- [ ] **Step 4: Run the test**

Run: `npm test -- hooks.test`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/finance/hooks.ts frontend/src/finance/hooks.test.tsx
git commit -m "feat(frontend): finance data hooks"
```

---

## Task 13: Watchlist table

**Files:**
- Create: `frontend/src/finance/WatchlistTable.tsx`
- Test: `frontend/src/finance/WatchlistTable.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/finance/WatchlistTable.test.tsx`:

```tsx
import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/utils';
import { WatchlistTable } from './WatchlistTable';
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
  {
    symbol: 'AAPL', price: 212.5, change: 1.8, change_pct: 0.85,
    volume: 1, as_of: '2026-05-20', sparkline: [1, 2, 3, 4, 5],
  },
];

test('renders a row for each quote', () => {
  renderWithProviders(<WatchlistTable quotes={quotes} />);
  expect(screen.getByText('AAPL')).toBeInTheDocument();
  expect(screen.getByText('+0.85%')).toBeInTheDocument();
});

test('adding a symbol calls the add mutation, upper-cased', async () => {
  renderWithProviders(<WatchlistTable quotes={quotes} />);
  await userEvent.type(screen.getByLabelText('Add symbol'), 'nvda');
  await userEvent.click(screen.getByRole('button', { name: 'Add' }));
  await waitFor(() => expect(addWatchlist).toHaveBeenCalledWith('NVDA'));
});

test('removing a symbol calls the remove mutation', async () => {
  renderWithProviders(<WatchlistTable quotes={quotes} />);
  await userEvent.click(screen.getByLabelText('Remove AAPL'));
  await waitFor(() => expect(removeWatchlist).toHaveBeenCalledWith('AAPL'));
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- WatchlistTable`
Expected: FAIL — `./WatchlistTable` does not exist.

- [ ] **Step 3: Create the watchlist table**

`frontend/src/finance/WatchlistTable.tsx`:

```tsx
import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import type { WatchlistQuote } from '../lib/types';
import { Sparkline } from '../charts/Sparkline';
import { trendColor } from '../charts/colors';
import { formatPercent, formatPrice } from '../lib/format';
import { useWatchlistMutations } from './hooks';
import { spring } from '../design/motion';

interface WatchlistTableProps {
  quotes: WatchlistQuote[];
}

export function WatchlistTable({ quotes }: WatchlistTableProps) {
  const { add, remove } = useWatchlistMutations();
  const [draft, setDraft] = useState('');

  function onAdd(e: FormEvent) {
    e.preventDefault();
    const symbol = draft.trim().toUpperCase();
    if (!symbol) return;
    add.mutate(symbol);
    setDraft('');
  }

  return (
    <div>
      <ul className="flex flex-col gap-0.5">
        <AnimatePresence initial={false}>
          {quotes.map((q) => (
            <motion.li
              key={q.symbol}
              layout
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={spring.snappy}
            >
              <WatchlistRow
                quote={q}
                onRemove={() => remove.mutate(q.symbol)}
              />
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>

      <form onSubmit={onAdd} className="mt-2 flex gap-1">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add symbol…"
          aria-label="Add symbol"
          className="min-w-0 flex-1 rounded-md border border-border bg-raised px-2 py-1
                     text-xs text-ink uppercase outline-none transition-colors
                     focus:border-accent"
        />
        <button
          type="submit"
          className="rounded-md border border-border px-2 py-1 text-xs text-ink-soft
                     transition-colors hover:border-border-strong"
        >
          Add
        </button>
      </form>
    </div>
  );
}

function WatchlistRow({
  quote,
  onRemove,
}: {
  quote: WatchlistQuote;
  onRemove: () => void;
}) {
  return (
    <div className="group flex items-center gap-2 rounded-md px-2 py-1.5
                    transition-colors hover:bg-raised">
      <Link
        to={`/finance/${encodeURIComponent(quote.symbol)}`}
        className="flex flex-1 items-center gap-3"
      >
        <span className="w-14 font-mono text-xs font-medium text-ink">
          {quote.symbol}
        </span>
        <Sparkline values={quote.sparkline} />
        <span className="ml-auto font-mono text-xs tabular-nums text-ink">
          {formatPrice(quote.price)}
        </span>
        <span
          className="w-16 text-right font-mono text-xs tabular-nums"
          style={{ color: trendColor(quote.change_pct) }}
        >
          {formatPercent(quote.change_pct)}
        </span>
      </Link>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${quote.symbol}`}
        className="text-ink-mute opacity-0 transition-opacity hover:text-down
                   group-hover:opacity-100"
      >
        ✕
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Run the test**

Run: `npm test -- WatchlistTable`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/finance/WatchlistTable.tsx frontend/src/finance/WatchlistTable.test.tsx
git commit -m "feat(frontend): watchlist table with add/remove"
```

---

## Task 14: Breadth gauge

**Files:**
- Create: `frontend/src/finance/BreadthGauge.tsx`
- Test: `frontend/src/finance/BreadthGauge.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/finance/BreadthGauge.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { BreadthGauge } from './BreadthGauge';

test('renders advancer/decliner counts and the A/D ratio', () => {
  render(
    <BreadthGauge
      breadth={{
        advancers: 12,
        decliners: 4,
        unchanged: 1,
        advance_decline_ratio: 3,
      }}
    />,
  );
  expect(screen.getByText(/12 adv/)).toBeInTheDocument();
  expect(screen.getByText(/4 dec/)).toBeInTheDocument();
  expect(screen.getByText(/3\.00 A\/D/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- BreadthGauge`
Expected: FAIL — `./BreadthGauge` does not exist.

- [ ] **Step 3: Create the breadth gauge**

`frontend/src/finance/BreadthGauge.tsx`:

```tsx
import { motion } from 'motion/react';
import type { Breadth } from '../lib/types';
import { tokens } from '../design/tokens';
import { spring } from '../design/motion';

/** Advance/decline breadth as an animated diverging bar. */
export function BreadthGauge({ breadth }: { breadth: Breadth }) {
  const total =
    breadth.advancers + breadth.decliners + breadth.unchanged || 1;
  const adv = (breadth.advancers / total) * 100;
  const unc = (breadth.unchanged / total) * 100;
  const dec = (breadth.decliners / total) * 100;

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] tracking-widest text-ink-mute
                         uppercase">
          Breadth
        </span>
        <span className="font-mono text-xs tabular-nums text-ink">
          {breadth.advance_decline_ratio.toFixed(2)} A/D
        </span>
      </div>
      <div className="mt-1.5 flex h-2 overflow-hidden rounded-full bg-raised">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${adv}%` }}
          transition={spring.smooth}
          style={{ background: tokens.color.up }}
        />
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${unc}%` }}
          transition={spring.smooth}
          style={{ background: tokens.color.flat }}
        />
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${dec}%` }}
          transition={spring.smooth}
          style={{ background: tokens.color.down }}
        />
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px]">
        <span style={{ color: tokens.color.up }}>
          {breadth.advancers} adv
        </span>
        <span style={{ color: tokens.color.down }}>
          {breadth.decliners} dec
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run the test**

Run: `npm test -- BreadthGauge`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/finance/BreadthGauge.tsx frontend/src/finance/BreadthGauge.test.tsx
git commit -m "feat(frontend): market breadth gauge"
```

---

## Task 15: Sector heatmap

**Files:**
- Create: `frontend/src/finance/SectorHeatmap.tsx`
- Test: `frontend/src/finance/SectorHeatmap.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/finance/SectorHeatmap.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { SectorHeatmap } from './SectorHeatmap';

test('renders a cell for each sector', () => {
  render(
    <SectorHeatmap
      sectors={[
        { symbol: 'XLK', name: 'Technology', change_pct: 1.2 },
        { symbol: 'XLF', name: 'Financials', change_pct: -0.5 },
        { symbol: 'XLE', name: 'Energy', change_pct: 0 },
      ]}
    />,
  );
  expect(screen.getByText('XLK')).toBeInTheDocument();
  expect(screen.getByText('XLF')).toBeInTheDocument();
  expect(screen.getByText('XLE')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- SectorHeatmap`
Expected: FAIL — `./SectorHeatmap` does not exist.

- [ ] **Step 3: Create the sector heatmap**

`frontend/src/finance/SectorHeatmap.tsx`:

```tsx
import { useState } from 'react';
import { motion } from 'motion/react';
import type { SectorChange } from '../lib/types';
import { heatColor } from '../charts/colors';
import { formatPercent } from '../lib/format';
import { spring } from '../design/motion';

/** Sector performance as a heat grid; hovering a cell shows its detail. */
export function SectorHeatmap({ sectors }: { sectors: SectorChange[] }) {
  const [hover, setHover] = useState<SectorChange | null>(null);

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] tracking-widest text-ink-mute
                         uppercase">
          Sectors
        </span>
        <span className="h-4 font-mono text-[10px] text-ink-soft">
          {hover ? `${hover.name} ${formatPercent(hover.change_pct)}` : ''}
        </span>
      </div>
      <div className="mt-1.5 grid grid-cols-4 gap-1">
        {sectors.map((s) => (
          <motion.div
            key={s.symbol}
            whileHover={{ scale: 1.06, zIndex: 1 }}
            transition={spring.snappy}
            onHoverStart={() => setHover(s)}
            onHoverEnd={() => setHover(null)}
            className="flex aspect-[5/3] flex-col justify-between rounded-sm p-1.5"
            style={{ background: heatColor(s.change_pct) }}
          >
            <span className="font-mono text-[9px] font-medium text-ink">
              {s.symbol}
            </span>
            <span className="font-mono text-[10px] tabular-nums text-ink">
              {formatPercent(s.change_pct, { sign: false })}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run the test**

Run: `npm test -- SectorHeatmap`
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/finance/SectorHeatmap.tsx frontend/src/finance/SectorHeatmap.test.tsx
git commit -m "feat(frontend): sector heatmap"
```

---

## Task 16: Index strip and Finance panel assembly

**Files:**
- Create: `frontend/src/finance/IndexStrip.tsx`, `frontend/src/finance/FinancePanel.tsx`
- Modify: `frontend/src/routes/Home.tsx` (swap the Finance placeholder for the real panel)
- Modify: `frontend/src/routes/Home.test.tsx` (replace the whole file)
- Test: `frontend/src/finance/FinancePanel.test.tsx`

- [ ] **Step 1: Create the index strip**

`frontend/src/finance/IndexStrip.tsx`:

```tsx
import type { Quote } from '../lib/types';
import { formatPercent } from '../lib/format';
import { trendColor } from '../charts/colors';

const SHORT_NAME: Record<string, string> = {
  '^GSPC': 'S&P',
  '^DJI': 'Dow',
  '^IXIC': 'Nasdaq',
  '^RUT': 'Rus2K',
  '^VIX': 'VIX',
};

/** A compact one-line summary of the major indices. */
export function IndexStrip({ indices }: { indices: Quote[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1">
      {indices.map((q) => (
        <div key={q.symbol} className="flex items-baseline gap-1.5">
          <span className="font-mono text-[10px] text-ink-mute">
            {SHORT_NAME[q.symbol] ?? q.symbol}
          </span>
          <span
            className="font-mono text-xs tabular-nums"
            style={{ color: trendColor(q.change_pct) }}
          >
            {formatPercent(q.change_pct)}
          </span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Write the failing test**

`frontend/src/finance/FinancePanel.test.tsx`:

```tsx
import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { FinancePanel } from './FinancePanel';

vi.mock('../lib/api', () => ({
  api: {
    overview: vi.fn().mockResolvedValue({
      watchlist: [
        {
          symbol: 'AAPL', price: 212.5, change: 1.8, change_pct: 0.85,
          volume: 1, as_of: '2026-05-20', sparkline: [1, 2, 3, 4],
        },
      ],
      indices: [
        {
          symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.22,
          volume: 0, as_of: '2026-05-20',
        },
      ],
      sectors: [{ symbol: 'XLK', name: 'Technology', change_pct: 1.1 }],
      breadth: {
        advancers: 2, decliners: 1, unchanged: 0, advance_decline_ratio: 2,
      },
      updated_at: '2026-05-20T20:00:00+00:00',
    }),
    addWatchlist: vi.fn(),
    removeWatchlist: vi.fn(),
  },
}));

test('shows a loading skeleton before data arrives', () => {
  renderWithProviders(<FinancePanel />);
  expect(screen.getByRole('status')).toBeInTheDocument();
});

test('renders watchlist, indices, sectors, and breadth once loaded', async () => {
  renderWithProviders(<FinancePanel />);
  await waitFor(() =>
    expect(screen.getByText('AAPL')).toBeInTheDocument(),
  );
  expect(screen.getByText('S&P')).toBeInTheDocument();
  expect(screen.getByText('XLK')).toBeInTheDocument();
  expect(screen.getByText(/2 adv/)).toBeInTheDocument();
});
```

- [ ] **Step 3: Run the test**

Run: `npm test -- FinancePanel`
Expected: FAIL — `./FinancePanel` does not exist.

- [ ] **Step 4: Create the Finance panel**

`frontend/src/finance/FinancePanel.tsx`:

```tsx
import { Panel } from '../components/Panel';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { useOverview } from './hooks';
import { WatchlistTable } from './WatchlistTable';
import { BreadthGauge } from './BreadthGauge';
import { SectorHeatmap } from './SectorHeatmap';
import { IndexStrip } from './IndexStrip';

/** The Finance quadrant: indices, watchlist, breadth, and sector heatmap. */
export function FinancePanel() {
  const { data, isLoading, isError, isStale } = useOverview();

  return (
    <Panel
      title="Finance"
      icon="💹"
      action={
        data ? (
          <span className="font-mono text-[10px] text-ink-mute">
            {isStale ? 'Stale · ' : ''}
            {formatUpdated(data.updated_at)}
          </span>
        ) : undefined
      }
    >
      {isLoading && <PanelSkeleton rows={6} />}
      {isError && (
        <p className="py-8 text-center text-sm text-down">
          Couldn't load market data.
        </p>
      )}
      {data && (
        <div className="flex flex-col gap-4">
          <IndexStrip indices={data.indices} />
          <WatchlistTable quotes={data.watchlist} />
          <BreadthGauge breadth={data.breadth} />
          <SectorHeatmap sectors={data.sectors} />
        </div>
      )}
    </Panel>
  );
}
```

- [ ] **Step 5: Swap the Finance placeholder into the Home route**

`frontend/src/routes/Home.tsx` (replace the whole file):

```tsx
import { AppShell } from '../components/AppShell';
import { QuadrantGrid } from '../components/QuadrantGrid';
import { ComingSoonPanel } from '../components/ComingSoonPanel';
import { FinancePanel } from '../finance/FinancePanel';

export function Home() {
  return (
    <AppShell>
      <QuadrantGrid
        news={<ComingSoonPanel title="News" icon="📰" phase="Phase 3" />}
        politics={<ComingSoonPanel title="Politics" icon="🏛" phase="Phase 4" />}
        economics={<ComingSoonPanel title="Economics" icon="📊" phase="Phase 2" />}
        finance={<FinancePanel />}
      />
    </AppShell>
  );
}
```

- [ ] **Step 6: Update the Home test for the data-backed Finance panel**

`frontend/src/routes/Home.test.tsx` (replace the whole file):

```tsx
import { vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { Home } from './Home';

vi.mock('../lib/api', () => ({
  api: {
    overview: vi.fn().mockResolvedValue({
      watchlist: [], indices: [], sectors: [],
      breadth: {
        advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0,
      },
      updated_at: '2026-05-20T20:00:00+00:00',
    }),
    addWatchlist: vi.fn(),
    removeWatchlist: vi.fn(),
  },
}));

test('renders the four-quadrant dashboard shell', () => {
  renderWithProviders(<Home />);
  expect(screen.getByText('NMD')).toBeInTheDocument();
  expect(screen.getByText('News')).toBeInTheDocument();
  expect(screen.getByText('Politics')).toBeInTheDocument();
  expect(screen.getByText('Economics')).toBeInTheDocument();
  expect(screen.getByText('Finance')).toBeInTheDocument();
});
```

- [ ] **Step 7: Run the tests**

Run: `npm test -- FinancePanel Home.test`
Expected: PASS (FinancePanel: 2, Home: 1).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/finance/IndexStrip.tsx frontend/src/finance/FinancePanel.tsx \
  frontend/src/finance/FinancePanel.test.tsx frontend/src/routes/Home.tsx \
  frontend/src/routes/Home.test.tsx
git commit -m "feat(frontend): index strip and Finance panel assembly"
```

---

## Task 17: Candlestick price chart with crosshair

**Files:**
- Create: `frontend/src/charts/CandlestickChart.tsx`
- Test: `frontend/src/charts/CandlestickChart.test.tsx`

This is the centerpiece visualization: OHLC candles, three moving-average overlays, gridlines, axes, and an interactive crosshair with an OHLC tooltip. It is one cohesive component file.

- [ ] **Step 1: Write the failing test**

`frontend/src/charts/CandlestickChart.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { CandlestickChart } from './CandlestickChart';
import type { Bar, Technicals } from '../lib/types';

function makeBars(n: number): Bar[] {
  return Array.from({ length: n }, (_, i) => {
    const date = new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10);
    return {
      date,
      open: 100 + i,
      high: 106 + i,
      low: 95 + i,
      close: 102 + i,
      volume: 1000,
    };
  });
}

test('renders one candle body per bar plus three SMA overlays', () => {
  const bars = makeBars(30);
  const technicals: Technicals = {
    sma_20: bars.map((b) => b.close),
    sma_50: bars.map(() => null),
    sma_200: bars.map(() => null),
  };
  const { container } = render(
    <CandlestickChart bars={bars} technicals={technicals} />,
  );
  expect(container.querySelectorAll('path')).toHaveLength(3);
  // one rect per candle body + the transparent pointer-capture overlay
  expect(container.querySelectorAll('rect')).toHaveLength(bars.length + 1);
});

test('renders nothing for an empty bar list without crashing', () => {
  const empty: Technicals = { sma_20: [], sma_50: [], sma_200: [] };
  const { container } = render(
    <CandlestickChart bars={[]} technicals={empty} />,
  );
  expect(container.querySelector('svg')).toBeNull();
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- CandlestickChart`
Expected: FAIL — `./CandlestickChart` does not exist.

- [ ] **Step 3: Create the candlestick chart**

`frontend/src/charts/CandlestickChart.tsx`:

```tsx
import { useMemo, useRef, useState } from 'react';
import type { MouseEvent } from 'react';
import { scaleBand, scaleLinear } from 'd3-scale';
import { curveMonotoneX, line } from 'd3-shape';
import { max, min } from 'd3-array';
import { ChartFrame } from './ChartFrame';
import { Axis } from './Axis';
import { useChartDimensions } from './useChartDimensions';
import { smaColor } from './colors';
import { tokens } from '../design/tokens';
import { formatDay, formatPrice } from '../lib/format';
import type { Bar, Technicals } from '../lib/types';

const MARGIN = { top: 10, right: 12, bottom: 26, left: 52 };

interface CandlestickChartProps {
  bars: Bar[];
  technicals: Technicals;
  height?: number;
}

/** Bespoke OHLC candlestick chart with SMA overlays and a crosshair tooltip. */
export function CandlestickChart({
  bars,
  technicals,
  height = 380,
}: CandlestickChartProps) {
  const [wrapRef, dims] = useChartDimensions<HTMLDivElement>({
    width: 820,
    height,
  });
  const [active, setActive] = useState<number | null>(null);
  const plotRef = useRef<SVGRectElement>(null);

  const g = useMemo(() => {
    const innerW = Math.max(0, dims.width - MARGIN.left - MARGIN.right);
    const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);
    if (bars.length === 0 || innerW <= 0) return null;

    const x = scaleBand<number>()
      .domain(bars.map((_, i) => i))
      .range([0, innerW])
      .padding(0.3);
    const lo = min(bars, (b) => b.low) ?? 0;
    const hi = max(bars, (b) => b.high) ?? 1;
    const pad = (hi - lo) * 0.06 || 1;
    const y = scaleLinear()
      .domain([lo - pad, hi + pad])
      .range([innerH, 0])
      .nice();
    const candleW = Math.max(1, x.bandwidth());
    const cx = (i: number) => (x(i) ?? 0) + candleW / 2;

    const smaPath = (values: (number | null)[]) =>
      line<{ i: number; v: number | null }>()
        .defined((d) => d.v != null && Number.isFinite(d.v))
        .x((d) => cx(d.i))
        .y((d) => y(d.v as number))
        .curve(curveMonotoneX)(values.map((v, i) => ({ i, v }))) ?? '';

    const step = Math.max(1, Math.ceil(bars.length / 6));
    const xTicks = bars
      .map((b, i) => ({ b, i }))
      .filter(({ i }) => i % step === 0)
      .map(({ b, i }) => ({ value: i, offset: cx(i), label: formatDay(b.date) }));
    const yTicks = y
      .ticks(5)
      .map((t) => ({ value: t, offset: y(t), label: t.toFixed(0) }));

    return { x, y, candleW, cx, innerW, innerH, smaPath, xTicks, yTicks };
  }, [bars, dims.width, height]);

  function onMove(e: MouseEvent) {
    if (!g || !plotRef.current || bars.length < 2) return;
    const box = plotRef.current.getBoundingClientRect();
    const rel = e.clientX - box.left;
    const i = Math.round((rel / g.innerW) * (bars.length - 1));
    setActive(Math.min(bars.length - 1, Math.max(0, i)));
  }

  const activeBar = active !== null ? bars[active] : null;

  if (!g) return null;

  return (
    <div ref={wrapRef} className="relative w-full">
      <ChartFrame
        width={dims.width}
        height={height}
        margin={MARGIN}
        label="Price history candlestick chart"
      >
        {() => (
          <>
            {g.yTicks.map((t) => (
              <line
                key={`grid-${t.value}`}
                x1={0}
                x2={g.innerW}
                y1={t.offset}
                y2={t.offset}
                stroke={tokens.color.border}
                strokeWidth={1}
              />
            ))}
            <Axis orientation="left" ticks={g.yTicks} />
            <Axis orientation="bottom" ticks={g.xTicks} />

            {bars.map((b, i) => {
              const up = b.close >= b.open;
              const color = up ? tokens.color.up : tokens.color.down;
              const bodyTop = Math.min(g.y(b.open), g.y(b.close));
              const bodyH = Math.max(1, Math.abs(g.y(b.close) - g.y(b.open)));
              return (
                <g
                  key={b.date}
                  opacity={active === null || active === i ? 1 : 0.5}
                >
                  <line
                    x1={g.cx(i)}
                    x2={g.cx(i)}
                    y1={g.y(b.high)}
                    y2={g.y(b.low)}
                    stroke={color}
                    strokeWidth={1}
                  />
                  <rect
                    x={g.x(i) ?? 0}
                    y={bodyTop}
                    width={g.candleW}
                    height={bodyH}
                    fill={color}
                    rx={Math.min(1, g.candleW / 3)}
                  />
                </g>
              );
            })}

            <path
              d={g.smaPath(technicals.sma_20)}
              fill="none"
              stroke={smaColor[20]}
              strokeWidth={1.25}
            />
            <path
              d={g.smaPath(technicals.sma_50)}
              fill="none"
              stroke={smaColor[50]}
              strokeWidth={1.25}
            />
            <path
              d={g.smaPath(technicals.sma_200)}
              fill="none"
              stroke={smaColor[200]}
              strokeWidth={1.25}
            />

            {activeBar && active !== null && (
              <line
                x1={g.cx(active)}
                x2={g.cx(active)}
                y1={0}
                y2={g.innerH}
                stroke={tokens.color.inkSoft}
                strokeWidth={1}
                strokeDasharray="3 3"
                pointerEvents="none"
              />
            )}

            <rect
              ref={plotRef}
              x={0}
              y={0}
              width={g.innerW}
              height={g.innerH}
              fill="transparent"
              onMouseMove={onMove}
              onMouseLeave={() => setActive(null)}
            />
          </>
        )}
      </ChartFrame>

      {activeBar && active !== null && (
        <div
          className="pointer-events-none absolute top-2 rounded-md border
                     border-border bg-raised/95 px-3 py-2 font-mono text-[11px]
                     shadow-lg"
          style={{
            left: Math.max(
              MARGIN.left,
              Math.min(dims.width - 150, MARGIN.left + g.cx(active)),
            ),
          }}
        >
          <div className="text-ink-soft">{formatDay(activeBar.date)}</div>
          <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-ink">
            <span className="text-ink-mute">O</span>
            <span>{formatPrice(activeBar.open)}</span>
            <span className="text-ink-mute">H</span>
            <span>{formatPrice(activeBar.high)}</span>
            <span className="text-ink-mute">L</span>
            <span>{formatPrice(activeBar.low)}</span>
            <span className="text-ink-mute">C</span>
            <span>{formatPrice(activeBar.close)}</span>
          </div>
        </div>
      )}

      <div className="mt-1 flex gap-4 px-1 font-mono text-[10px] text-ink-mute">
        <LegendDot color={smaColor[20]} label="SMA 20" />
        <LegendDot color={smaColor[50]} label="SMA 50" />
        <LegendDot color={smaColor[200]} label="SMA 200" />
      </div>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1">
      <span
        className="inline-block h-1.5 w-3 rounded-full"
        style={{ background: color }}
      />
      {label}
    </span>
  );
}
```

- [ ] **Step 4: Run the test**

Run: `npm test -- CandlestickChart`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/charts/CandlestickChart.tsx frontend/src/charts/CandlestickChart.test.tsx
git commit -m "feat(frontend): candlestick price chart with crosshair"
```

---

## Task 18: Fundamentals grid and stats row

**Files:**
- Create: `frontend/src/finance/FundamentalsGrid.tsx`, `frontend/src/finance/StatsRow.tsx`
- Test: `frontend/src/finance/instrumentPanels.test.tsx`

- [ ] **Step 1: Write the failing test**

`frontend/src/finance/instrumentPanels.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { buildFundamentalCells, FundamentalsGrid } from './FundamentalsGrid';
import { StatsRow } from './StatsRow';
import type { Fundamentals } from '../lib/types';

const full: Fundamentals = {
  symbol: 'AAPL', name: 'Apple Inc.', sector: 'Technology',
  industry: 'Consumer Electronics', market_cap: 3.21e12, pe_ratio: 29.4,
  price_to_book: 48.1, dividend_yield: 0.5, week52_high: 240,
  week52_low: 160, beta: 1.2,
};

test('buildFundamentalCells formats the market cap compactly', () => {
  const cells = buildFundamentalCells(full);
  expect(cells.find((c) => c.label === 'Market Cap')?.value).toBe('3.21T');
});

test('buildFundamentalCells renders an em dash for missing values', () => {
  const cells = buildFundamentalCells({ ...full, pe_ratio: null, beta: null });
  expect(cells.find((c) => c.label === 'P/E')?.value).toBe('—');
  expect(cells.find((c) => c.label === 'Beta')?.value).toBe('—');
});

test('FundamentalsGrid renders every field label', () => {
  render(<FundamentalsGrid profile={full} />);
  expect(screen.getByText('Market Cap')).toBeInTheDocument();
  expect(screen.getByText('Beta')).toBeInTheDocument();
});

test('StatsRow renders momentum and volatility stats', () => {
  render(
    <StatsRow
      stats={{
        momentum_1m: 4.2, momentum_3m: 9.1, momentum_6m: -3.4,
        volatility_30d: 22.5, week52_high: 240, week52_low: 160,
      }}
    />,
  );
  expect(screen.getByText('1M')).toBeInTheDocument();
  expect(screen.getByText('+4.20%')).toBeInTheDocument();
  expect(screen.getByText('Vol 30D')).toBeInTheDocument();
  expect(screen.getByText('22.50%')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- instrumentPanels`
Expected: FAIL — `./FundamentalsGrid` does not exist.

- [ ] **Step 3: Create the fundamentals grid**

`frontend/src/finance/FundamentalsGrid.tsx`:

```tsx
import type { Fundamentals } from '../lib/types';
import { formatCompact, formatPercent, formatPrice } from '../lib/format';

export interface FundamentalCell {
  label: string;
  value: string;
}

/** Build the display cells for a fundamentals profile (pure — testable). */
export function buildFundamentalCells(p: Fundamentals): FundamentalCell[] {
  const fmt = (n: number | null, f: (x: number) => string) =>
    n == null ? '—' : f(n);
  return [
    { label: 'Market Cap', value: formatCompact(p.market_cap) },
    { label: 'P/E', value: fmt(p.pe_ratio, (x) => x.toFixed(1)) },
    { label: 'P/B', value: fmt(p.price_to_book, (x) => x.toFixed(2)) },
    {
      label: 'Div Yield',
      value: fmt(p.dividend_yield, (x) => formatPercent(x, { sign: false })),
    },
    { label: 'Beta', value: fmt(p.beta, (x) => x.toFixed(2)) },
    { label: '52W High', value: fmt(p.week52_high, formatPrice) },
    { label: '52W Low', value: fmt(p.week52_low, formatPrice) },
  ];
}

export function FundamentalsGrid({ profile }: { profile: Fundamentals }) {
  const cells = buildFundamentalCells(profile);
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border
                    border-border bg-border sm:grid-cols-4">
      {cells.map((c) => (
        <div key={c.label} className="bg-surface px-3 py-2">
          <div className="font-mono text-[10px] tracking-wide text-ink-mute
                          uppercase">
            {c.label}
          </div>
          <div className="mt-0.5 font-mono text-sm tabular-nums text-ink">
            {c.value}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Create the stats row**

`frontend/src/finance/StatsRow.tsx`:

```tsx
import type { InstrumentStats } from '../lib/types';
import { formatPercent } from '../lib/format';
import { trendColor } from '../charts/colors';
import { tokens } from '../design/tokens';

/** Momentum (1M/3M/6M) and 30-day volatility as compact stat tiles. */
export function StatsRow({ stats }: { stats: InstrumentStats }) {
  const items = [
    { label: '1M', value: stats.momentum_1m, signed: true },
    { label: '3M', value: stats.momentum_3m, signed: true },
    { label: '6M', value: stats.momentum_6m, signed: true },
    { label: 'Vol 30D', value: stats.volatility_30d, signed: false },
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it) => (
        <div
          key={it.label}
          className="flex flex-col rounded-md border border-border bg-surface
                     px-3 py-2"
        >
          <span className="font-mono text-[10px] tracking-wide text-ink-mute
                           uppercase">
            {it.label}
          </span>
          <span
            className="font-mono text-sm tabular-nums"
            style={{
              color: it.signed ? trendColor(it.value) : tokens.color.ink,
            }}
          >
            {formatPercent(it.value, { sign: it.signed })}
          </span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Run the test**

Run: `npm test -- instrumentPanels`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/finance/FundamentalsGrid.tsx frontend/src/finance/StatsRow.tsx \
  frontend/src/finance/instrumentPanels.test.tsx
git commit -m "feat(frontend): fundamentals grid and stats row"
```

---

## Task 19: Instrument drill-down page with shared-element transition

**Files:**
- Modify: `frontend/src/routes/InstrumentRoute.tsx` (replace the whole file)
- Modify: `frontend/src/finance/WatchlistTable.tsx` (replace the whole file)
- Test: `frontend/src/routes/InstrumentRoute.test.tsx`

The drill-down opens with a **shared-element transition**: the clicked watchlist row's sparkline morphs into the instrument page's chart panel. Both elements carry the `view-transition-name: instrument-hero`; React Router's `viewTransition` prop drives `document.startViewTransition`. The `prefers-reduced-motion` rule added to `index.css` in Task 2 disables the morph animation.

- [ ] **Step 1: Write the failing test**

`frontend/src/routes/InstrumentRoute.test.tsx`:

```tsx
import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { InstrumentRoute } from './InstrumentRoute';

const instrument = {
  symbol: 'AAPL',
  profile: {
    symbol: 'AAPL', name: 'Apple Inc.', sector: 'Technology',
    industry: 'Consumer Electronics', market_cap: 3.21e12, pe_ratio: 29.4,
    price_to_book: 48.1, dividend_yield: 0.5, week52_high: 240,
    week52_low: 160, beta: 1.2,
  },
  bars: [
    { date: '2026-01-02', open: 100, high: 104, low: 98, close: 102, volume: 1 },
    { date: '2026-01-03', open: 102, high: 106, low: 101, close: 105, volume: 1 },
  ],
  technicals: {
    sma_20: [null, null], sma_50: [null, null], sma_200: [null, null],
  },
  stats: {
    momentum_1m: 4.2, momentum_3m: 9.1, momentum_6m: 15.3,
    volatility_30d: 22.5, week52_high: 240, week52_low: 160,
  },
  updated_at: '2026-05-20T20:00:00+00:00',
};

const instrumentFn = vi.fn();
vi.mock('../lib/api', () => ({
  api: { instrument: (s: string) => instrumentFn(s) },
}));

test('renders the drill-down page for a symbol', async () => {
  instrumentFn.mockResolvedValueOnce(instrument);
  renderWithProviders(<InstrumentRoute />, {
    route: '/finance/AAPL',
    path: '/finance/:symbol',
  });
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: 'AAPL' })).toBeInTheDocument(),
  );
  expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
  expect(screen.getByText('Fundamentals')).toBeInTheDocument();
  expect(screen.getByText('SMA 20')).toBeInTheDocument();
});

test('shows an error message when the instrument has no data', async () => {
  instrumentFn.mockRejectedValueOnce(new Error('404'));
  renderWithProviders(<InstrumentRoute />, {
    route: '/finance/ZZZZ',
    path: '/finance/:symbol',
  });
  await waitFor(() =>
    expect(
      screen.getByText(/No data available for ZZZZ/),
    ).toBeInTheDocument(),
  );
});
```

- [ ] **Step 2: Run the test**

Run: `npm test -- InstrumentRoute`
Expected: FAIL — `InstrumentRoute` is still the Task 11 stub.

- [ ] **Step 3: Replace the instrument route with the full drill-down page**

`frontend/src/routes/InstrumentRoute.tsx` (replace the whole file):

```tsx
import { Link, useParams } from 'react-router-dom';
import { motion } from 'motion/react';
import { useInstrument } from '../finance/hooks';
import { CandlestickChart } from '../charts/CandlestickChart';
import { FundamentalsGrid } from '../finance/FundamentalsGrid';
import { StatsRow } from '../finance/StatsRow';
import { AppShell } from '../components/AppShell';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { spring } from '../design/motion';

export function InstrumentRoute() {
  const { symbol = '' } = useParams();
  const upper = symbol.toUpperCase();
  const { data, isLoading, isError } = useInstrument(upper);

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl p-4">
        <Link
          to="/"
          viewTransition
          className="font-mono text-xs text-ink-soft transition-colors
                     hover:text-accent"
        >
          ← Dashboard
        </Link>

        {isLoading && (
          <div className="mt-4">
            <PanelSkeleton rows={8} />
          </div>
        )}

        {isError && (
          <p className="mt-8 text-center text-sm text-down">
            No data available for {upper}.
          </p>
        )}

        {data && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring.gentle}
            className="mt-3"
          >
            <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h1 className="font-mono text-2xl font-semibold text-ink">
                {data.symbol}
              </h1>
              <span className="text-sm text-ink-soft">{data.profile.name}</span>
            </header>

            <div
              className="mt-4 rounded-lg border border-border bg-surface p-4"
              style={{ viewTransitionName: 'instrument-hero' }}
            >
              <CandlestickChart bars={data.bars} technicals={data.technicals} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Momentum &amp; Risk
            </h2>
            <div className="mt-2">
              <StatsRow stats={data.stats} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Fundamentals
            </h2>
            <div className="mt-2">
              <FundamentalsGrid profile={data.profile} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Why this matters
            </h2>
            <p className="mt-2 rounded-md border border-dashed border-border
                          bg-surface px-3 py-3 text-sm text-ink-mute">
              AI-generated context for this instrument arrives in a later phase.
            </p>

            <p className="mt-6 font-mono text-[10px] text-ink-mute">
              {formatUpdated(data.updated_at)}
            </p>
          </motion.div>
        )}
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 4: Add the shared-element source to the watchlist row**

`frontend/src/finance/WatchlistTable.tsx` (replace the whole file):

```tsx
import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useViewTransitionState } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import type { WatchlistQuote } from '../lib/types';
import { Sparkline } from '../charts/Sparkline';
import { trendColor } from '../charts/colors';
import { formatPercent, formatPrice } from '../lib/format';
import { useWatchlistMutations } from './hooks';
import { spring } from '../design/motion';

interface WatchlistTableProps {
  quotes: WatchlistQuote[];
}

export function WatchlistTable({ quotes }: WatchlistTableProps) {
  const { add, remove } = useWatchlistMutations();
  const [draft, setDraft] = useState('');

  function onAdd(e: FormEvent) {
    e.preventDefault();
    const symbol = draft.trim().toUpperCase();
    if (!symbol) return;
    add.mutate(symbol);
    setDraft('');
  }

  return (
    <div>
      <ul className="flex flex-col gap-0.5">
        <AnimatePresence initial={false}>
          {quotes.map((q) => (
            <motion.li
              key={q.symbol}
              layout
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={spring.snappy}
            >
              <WatchlistRow
                quote={q}
                onRemove={() => remove.mutate(q.symbol)}
              />
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>

      <form onSubmit={onAdd} className="mt-2 flex gap-1">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add symbol…"
          aria-label="Add symbol"
          className="min-w-0 flex-1 rounded-md border border-border bg-raised px-2 py-1
                     text-xs text-ink uppercase outline-none transition-colors
                     focus:border-accent"
        />
        <button
          type="submit"
          className="rounded-md border border-border px-2 py-1 text-xs text-ink-soft
                     transition-colors hover:border-border-strong"
        >
          Add
        </button>
      </form>
    </div>
  );
}

function WatchlistRow({
  quote,
  onRemove,
}: {
  quote: WatchlistQuote;
  onRemove: () => void;
}) {
  const to = `/finance/${encodeURIComponent(quote.symbol)}`;
  // True while a view transition to this row's drill-down is in flight —
  // gives the sparkline the shared name so it morphs into the chart panel.
  const transitioning = useViewTransitionState(to);

  return (
    <div className="group flex items-center gap-2 rounded-md px-2 py-1.5
                    transition-colors hover:bg-raised">
      <Link to={to} viewTransition className="flex flex-1 items-center gap-3">
        <span className="w-14 font-mono text-xs font-medium text-ink">
          {quote.symbol}
        </span>
        <span
          style={
            transitioning
              ? { viewTransitionName: 'instrument-hero' }
              : undefined
          }
        >
          <Sparkline values={quote.sparkline} />
        </span>
        <span className="ml-auto font-mono text-xs tabular-nums text-ink">
          {formatPrice(quote.price)}
        </span>
        <span
          className="w-16 text-right font-mono text-xs tabular-nums"
          style={{ color: trendColor(quote.change_pct) }}
        >
          {formatPercent(quote.change_pct)}
        </span>
      </Link>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${quote.symbol}`}
        className="text-ink-mute opacity-0 transition-opacity hover:text-down
                   group-hover:opacity-100"
      >
        ✕
      </button>
    </div>
  );
}
```

- [ ] **Step 5: Run the tests**

Run: `npm test -- InstrumentRoute WatchlistTable`
Expected: PASS (InstrumentRoute: 2, WatchlistTable: 3 — still green).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/InstrumentRoute.tsx frontend/src/routes/InstrumentRoute.test.tsx \
  frontend/src/finance/WatchlistTable.tsx
git commit -m "feat(frontend): instrument drill-down page with shared-element transition"
```

---

## Task 20: End-to-end test and final verification

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/overview-to-drilldown.spec.ts`
- Modify: `frontend/README.md` (replace the whole file)

- [ ] **Step 1: Create the Playwright config**

`frontend/playwright.config.ts`:

```ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
```

- [ ] **Step 2: Write the end-to-end test**

`frontend/e2e/overview-to-drilldown.spec.ts`:

```ts
import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

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

function makeBars(n: number) {
  const bars = [];
  let price = 180;
  for (let i = 0; i < n; i++) {
    price += Math.sin(i / 7) * 2;
    const date = new Date(Date.UTC(2024, 0, 1 + i)).toISOString().slice(0, 10);
    bars.push({
      date,
      open: price,
      high: price + 3,
      low: price - 3,
      close: price + 1,
      volume: 1_000_000,
    });
  }
  return bars;
}

const instrument = {
  symbol: 'AAPL',
  profile: {
    symbol: 'AAPL', name: 'Apple Inc.', sector: 'Technology',
    industry: 'Consumer Electronics', market_cap: 3.21e12, pe_ratio: 29.4,
    price_to_book: 48.1, dividend_yield: 0.5, week52_high: 240,
    week52_low: 160, beta: 1.2,
  },
  bars: makeBars(120),
  technicals: {
    sma_20: makeBars(120).map((b) => b.close),
    sma_50: makeBars(120).map((b) => b.close),
    sma_200: makeBars(120).map(() => null),
  },
  stats: {
    momentum_1m: 4.2, momentum_3m: 9.1, momentum_6m: 15.3,
    volatility_30d: 22.5, week52_high: 240, week52_low: 160,
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
  await page.route('**/api/finance/instrument/**', (route) =>
    route.fulfill({ json: instrument }),
  );
}

test('the overview drills down into an instrument page', async ({ page }) => {
  await stubApi(page);
  await page.goto('/');

  await expect(page.getByText('NMD')).toBeVisible();
  await expect(page.getByText('AAPL')).toBeVisible();

  await page.getByRole('link', { name: /AAPL/ }).click();

  await expect(page).toHaveURL(/\/finance\/AAPL$/);
  await expect(page.getByRole('heading', { name: 'AAPL' })).toBeVisible();
  await expect(page.getByText('Apple Inc.')).toBeVisible();
  await expect(page.getByText('Fundamentals')).toBeVisible();
});
```

- [ ] **Step 3: Install the Playwright browser**

Run: `npx playwright install chromium`
Expected: Chromium downloads successfully.

- [ ] **Step 4: Run the end-to-end test**

Run: `npm run test:e2e`
Expected: PASS (1 test) — Playwright starts the dev server, stubs the API, and the drill-down flow succeeds.

- [ ] **Step 5: Replace the README with the final version**

`frontend/README.md` (replace the whole file):

```markdown
# News & Markets Dashboard — Frontend

The React + TypeScript single-page app for the News & Markets Dashboard — a
four-quadrant overview (News, Politics, Economics, Finance) with the Finance
domain built end-to-end: a live overview panel and a per-instrument drill-down.

## Stack

- Vite + React 19 + TypeScript
- Tailwind CSS v4 with a CSS-first design-token layer
- Motion (Framer Motion) for animation; the View Transitions API for
  route-level morphs
- D3 for bespoke charts (sparkline, candlestick)
- TanStack Query for data fetching/caching; React Router v7 for routing

## Setup

    npm install
    cp .env.example .env

`VITE_API_BASE_URL` points at the backend (default `http://127.0.0.1:8000`).

## Scripts

- `npm run dev` — dev server on http://localhost:5173
- `npm run build` — type-check and production build
- `npm run preview` — preview the production build
- `npm test` — unit & component tests (Vitest)
- `npm run test:e2e` — end-to-end tests (Playwright)
- `npm run lint` — type-check only

## Running the full app

1. Start the backend: `cd ../backend && uvicorn app.main:app`
2. Start the frontend: `npm run dev`

Tests mock the backend and do not require it to be running.

## Architecture

- `src/design/` — design tokens and motion presets (the visual language)
- `src/charts/` — the D3-in-React chart system (frame, axis, sparkline,
  candlestick); every visualization is bespoke
- `src/lib/` — API client, types, formatters
- `src/auth/` — single-user token gate
- `src/components/` — app shell and the generic domain panel
- `src/finance/` — the Finance domain (overview panel + drill-down pieces)
- `src/routes/` — the Home dashboard and the instrument drill-down route
```

- [ ] **Step 6: Run the full unit/component suite and the build**

Run: `npm test`
Expected: PASS — every Vitest suite green.

Run: `npm run build`
Expected: type-check passes and Vite produces `dist/` with no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/playwright.config.ts frontend/e2e frontend/README.md
git commit -m "test(frontend): end-to-end overview-to-drilldown flow"
```

---

## Done criteria

Phase 1b is complete when:
- All Vitest suites pass (`npm test`) and the Playwright E2E passes (`npm run test:e2e`).
- `npm run build` succeeds with no type errors.
- Running the backend + `npm run dev` shows the four-quadrant Home with a live
  Finance panel, and clicking a watchlist row morphs into the instrument
  drill-down page.
- The News, Politics, and Economics quadrants show calm "coming soon"
  placeholders; the AI briefing ribbon shows its placeholder.
- All motion honors `prefers-reduced-motion`.

**Next:** Plan 1c — Deploy Pipeline (Fly.io backend, Vercel frontend, Supabase
Postgres).
