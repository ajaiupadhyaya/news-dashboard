# Finance Enrichment — Drill-down & Chart System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the instrument drill-down page with a multi-mode price chart (candle/line/area + SMA + Bollinger), RSI/MACD/volume sub-charts, timeframe selection, and a returns table — plus a ⌘K command palette.

**Architecture:** Frontend-only, additive. The Finance backend (technical indicators, `?range=`) is already built and live in the API. New shared chart pieces under `frontend/src/charts/`; the `InstrumentRoute` is rewritten to compose them; a `CommandPalette` is wired into the app shell. Reuses the existing chart design system (`ChartFrame`, `Axis`, `useChartDimensions`, design tokens, Motion).

**Tech Stack:** Vite + React 19 + TypeScript, D3 (d3-scale/shape/array), Motion, TanStack Query v5, React Router 7, Vitest + Testing Library, Playwright.

**Spec:** `docs/superpowers/specs/2026-05-22-finance-economics-enrichment-design.md` (§5.2, §7)

**Scope note:** This is Plan A of the Finance frontend — the **instrument drill-down + chart system + command palette**. Plan B (the bento `/finance` domain page) follows and reuses these chart components. Timeframe ranges are daily-interval only (`1mo`/`3mo`/`6mo`/`1y`/`5y`/`max`) — matching the backend.

**Conventions** (verified against the codebase):
- Tests run from `frontend/`: `npx vitest run src/<path>`. Type-check: `npx tsc --noEmit`.
- New backend type fields are typed **optional** on the frontend (`rsi?`, `returns?`, …) even though the backend always sends them — this keeps existing test fixtures valid and makes consumers degrade gracefully. Consumers default with `?? []`.
- Charts follow the existing pattern: `useChartDimensions` + `ChartFrame` + `Axis`, design tokens for SVG colors, `useReducedMotion` where animated, return `null` when there is too little data.
- Commit messages: `feat(frontend):` / `test(frontend):`.

---

## Task 1: Frontend types + API client for the enriched instrument

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Test: `frontend/src/lib/api.test.ts` (append)

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/lib/api.test.ts`:

```ts
test('instrument requests include the range query param', async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ symbol: 'AAPL' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
  vi.stubGlobal('fetch', fetchMock);
  const { api } = await import('./api');
  await api.instrument('AAPL', '5y');
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('/api/finance/instrument/AAPL?range=5y'),
    expect.anything(),
  );
  vi.unstubAllGlobals();
});

test('instrument defaults the range to 1y', async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ symbol: 'AAPL' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
  vi.stubGlobal('fetch', fetchMock);
  const { api } = await import('./api');
  await api.instrument('AAPL');
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining('range=1y'),
    expect.anything(),
  );
  vi.unstubAllGlobals();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/lib/api.test.ts`
Expected: FAIL — `api.instrument` ignores the second argument.

- [ ] **Step 3: Extend the types**

In `frontend/src/lib/types.ts`, REPLACE the existing `Technicals` interface with:

```ts
export interface Technicals {
  sma_20: (number | null)[];
  sma_50: (number | null)[];
  sma_200: (number | null)[];
  // Enrichment fields — the backend always sends these; optional here so
  // older fixtures stay valid and consumers degrade gracefully.
  rsi?: (number | null)[];
  macd_line?: (number | null)[];
  macd_signal?: (number | null)[];
  macd_histogram?: (number | null)[];
  bb_upper?: (number | null)[];
  bb_middle?: (number | null)[];
  bb_lower?: (number | null)[];
  volume?: number[];
}
```

Add a `Returns` interface immediately before `InstrumentResponse`:

```ts
export interface Returns {
  week_1: number | null;
  month_1: number | null;
  month_3: number | null;
  month_6: number | null;
  ytd: number | null;
  year_1: number | null;
  year_3: number | null;
}
```

In the `InstrumentResponse` interface, add the `returns` field after `stats`:

```ts
export interface InstrumentResponse {
  symbol: string;
  profile: Fundamentals;
  bars: Bar[];
  technicals: Technicals;
  stats: InstrumentStats;
  returns?: Returns;
  updated_at: string;
}
```

- [ ] **Step 4: Update the API client**

In `frontend/src/lib/api.ts`, REPLACE the existing `instrument` endpoint function with:

```ts
  instrument: (symbol: string, range = '1y') =>
    apiFetch<InstrumentResponse>(
      `/api/finance/instrument/${encodeURIComponent(symbol)}?range=${range}`,
    ),
```

- [ ] **Step 5: Run the tests + type-check to verify they pass**

Run: `npx vitest run src/lib/api.test.ts` — Expected: PASS.
Run: `npx tsc --noEmit` — Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/lib/api.test.ts
git commit -m "feat(frontend): add enriched instrument types and range param"
```

---

## Task 2: Instrument hook with timeframe range

**Files:**
- Modify: `frontend/src/finance/hooks.ts`
- Test: `frontend/src/finance/hooks.test.tsx` (append)

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/finance/hooks.test.tsx`:

```tsx
test('useInstrument passes the range through to the API', async () => {
  const { renderHook, waitFor } = await import('@testing-library/react');
  const { QueryWrapper } = await import('../test/utils');
  const { useInstrument } = await import('./hooks');
  const { api } = await import('../lib/api');

  const spy = vi
    .spyOn(api, 'instrument')
    .mockResolvedValue({ symbol: 'AAPL' } as never);
  const { result } = renderHook(() => useInstrument('AAPL', '5y'), {
    wrapper: QueryWrapper,
  });
  await waitFor(() => expect(result.current.isSuccess).toBe(true));
  expect(spy).toHaveBeenCalledWith('AAPL', '5y');
  spy.mockRestore();
});
```

Note: `hooks.test.tsx` already imports `vi`. If it does not, add `import { vi } from 'vitest';` at the top.

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/finance/hooks.test.tsx`
Expected: FAIL — `useInstrument` calls `api.instrument(symbol)` without the range.

- [ ] **Step 3: Update the hook**

In `frontend/src/finance/hooks.ts`, add `keepPreviousData` to the TanStack import and REPLACE the existing `useInstrument` function:

```ts
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
```

```ts
/**
 * A single instrument's drill-down data for a timeframe range. Disabled for
 * an empty symbol. Keeps the previous data while a new range loads, so
 * switching timeframes does not flash the page.
 */
export function useInstrument(symbol: string, range = '1y') {
  return useQuery({
    queryKey: ['instrument', symbol, range],
    queryFn: () => api.instrument(symbol, range),
    enabled: symbol.length > 0,
    placeholderData: keepPreviousData,
  });
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npx vitest run src/finance/hooks.test.tsx` — Expected: PASS.
Run: `npx tsc --noEmit` — Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/finance/hooks.ts frontend/src/finance/hooks.test.tsx
git commit -m "feat(frontend): add timeframe range to the instrument hook"
```

---

## Task 3: Chart controls — TimeframeControl and ChartTypeToggle

**Files:**
- Create: `frontend/src/charts/ChartControls.tsx`
- Test: `frontend/src/charts/ChartControls.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/charts/ChartControls.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { TimeframeControl, ChartTypeToggle } from './ChartControls';

test('TimeframeControl renders all timeframes and marks the active one', () => {
  render(<TimeframeControl value="1y" onChange={() => {}} />);
  expect(screen.getByRole('button', { name: '1M' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'MAX' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '1Y' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
});

test('TimeframeControl reports the chosen timeframe', () => {
  const onChange = vi.fn();
  render(<TimeframeControl value="1y" onChange={onChange} />);
  fireEvent.click(screen.getByRole('button', { name: '5Y' }));
  expect(onChange).toHaveBeenCalledWith('5y');
});

test('ChartTypeToggle reports the chosen type', () => {
  const onChange = vi.fn();
  render(<ChartTypeToggle value="candle" onChange={onChange} />);
  fireEvent.click(screen.getByRole('button', { name: 'Line' }));
  expect(onChange).toHaveBeenCalledWith('line');
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/charts/ChartControls.test.tsx`
Expected: FAIL — cannot resolve `./ChartControls`.

- [ ] **Step 3: Create the controls**

Create `frontend/src/charts/ChartControls.tsx`:

```tsx
import { clsx } from 'clsx';

export const TIMEFRAMES = ['1mo', '3mo', '6mo', '1y', '5y', 'max'] as const;
export type Timeframe = (typeof TIMEFRAMES)[number];

const TIMEFRAME_LABEL: Record<Timeframe, string> = {
  '1mo': '1M', '3mo': '3M', '6mo': '6M', '1y': '1Y', '5y': '5Y', max: 'MAX',
};

export const CHART_TYPES = ['candle', 'line', 'area'] as const;
export type ChartType = (typeof CHART_TYPES)[number];

const CHART_TYPE_LABEL: Record<ChartType, string> = {
  candle: 'Candles', line: 'Line', area: 'Area',
};

interface SegmentedProps<T extends string> {
  options: readonly T[];
  labels: Record<T, string>;
  value: T;
  onChange: (next: T) => void;
  ariaLabel: string;
}

/** A small segmented button group — the shared look for chart controls. */
function Segmented<T extends string>({
  options, labels, value, onChange, ariaLabel,
}: SegmentedProps<T>) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className="flex gap-0.5 rounded-md border border-border bg-raised p-0.5"
    >
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          aria-pressed={value === opt}
          onClick={() => onChange(opt)}
          className={clsx(
            'rounded px-2 py-0.5 font-mono text-[10px] transition-colors',
            value === opt
              ? 'bg-accent text-bg'
              : 'text-ink-mute hover:text-ink',
          )}
        >
          {labels[opt]}
        </button>
      ))}
    </div>
  );
}

/** Timeframe selector — 1M / 3M / 6M / 1Y / 5Y / MAX. */
export function TimeframeControl({
  value, onChange,
}: {
  value: Timeframe;
  onChange: (next: Timeframe) => void;
}) {
  return (
    <Segmented
      options={TIMEFRAMES}
      labels={TIMEFRAME_LABEL}
      value={value}
      onChange={onChange}
      ariaLabel="Timeframe"
    />
  );
}

/** Chart-type toggle — Candles / Line / Area. */
export function ChartTypeToggle({
  value, onChange,
}: {
  value: ChartType;
  onChange: (next: ChartType) => void;
}) {
  return (
    <Segmented
      options={CHART_TYPES}
      labels={CHART_TYPE_LABEL}
      value={value}
      onChange={onChange}
      ariaLabel="Chart type"
    />
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npx vitest run src/charts/ChartControls.test.tsx` — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/charts/ChartControls.tsx frontend/src/charts/ChartControls.test.tsx
git commit -m "feat(frontend): add timeframe and chart-type controls"
```

---

## Task 4: PriceChart — candle/line/area with SMA and Bollinger

**Files:**
- Create: `frontend/src/charts/PriceChart.tsx`
- Test: `frontend/src/charts/PriceChart.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/charts/PriceChart.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { PriceChart } from './PriceChart';
import type { Bar, Technicals } from '../lib/types';

function makeBars(n: number): Bar[] {
  return Array.from({ length: n }, (_, i) => ({
    date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
    open: 100 + i, high: 106 + i, low: 95 + i, close: 102 + i, volume: 1000,
  }));
}

const emptyTechnicals: Technicals = {
  sma_20: [], sma_50: [], sma_200: [],
};

test('candle mode renders one body rect per bar', () => {
  const bars = makeBars(20);
  const { container } = render(
    <PriceChart bars={bars} technicals={emptyTechnicals}
      chartType="candle" showSma={false} showBollinger={false} />,
  );
  // 20 candle bodies + 1 transparent pointer-capture overlay
  expect(container.querySelectorAll('rect').length).toBe(21);
});

test('line mode renders a price path, no candle bodies', () => {
  const bars = makeBars(20);
  const { container } = render(
    <PriceChart bars={bars} technicals={emptyTechnicals}
      chartType="line" showSma={false} showBollinger={false} />,
  );
  expect(container.querySelectorAll('path').length).toBeGreaterThan(0);
  // only the pointer-capture overlay rect
  expect(container.querySelectorAll('rect').length).toBe(1);
});

test('renders nothing for empty bars', () => {
  const { container } = render(
    <PriceChart bars={[]} technicals={emptyTechnicals}
      chartType="candle" showSma={false} showBollinger={false} />,
  );
  expect(container.querySelector('svg')).toBeNull();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/charts/PriceChart.test.tsx`
Expected: FAIL — cannot resolve `./PriceChart`.

- [ ] **Step 3: Create the chart**

Create `frontend/src/charts/PriceChart.tsx`:

```tsx
import { useMemo, useRef, useState } from 'react';
import type { MouseEvent } from 'react';
import { scaleBand, scaleLinear } from 'd3-scale';
import { area, curveMonotoneX, line } from 'd3-shape';
import { max, min } from 'd3-array';
import { ChartFrame } from './ChartFrame';
import { Axis } from './Axis';
import { useChartDimensions } from './useChartDimensions';
import { smaColor } from './colors';
import { tokens } from '../design/tokens';
import { formatDay, formatPrice } from '../lib/format';
import type { Bar, Technicals } from '../lib/types';
import type { ChartType } from './ChartControls';

const MARGIN = { top: 10, right: 12, bottom: 26, left: 52 };

interface PriceChartProps {
  bars: Bar[];
  technicals: Technicals;
  chartType: ChartType;
  showSma: boolean;
  showBollinger: boolean;
  height?: number;
}

/** The instrument price chart — candle / line / area, with optional SMA
 *  and Bollinger-band overlays and an OHLC crosshair tooltip. */
export function PriceChart({
  bars, technicals, chartType, showSma, showBollinger, height = 380,
}: PriceChartProps) {
  const [wrapRef, dims] = useChartDimensions<HTMLDivElement>({
    width: 820, height,
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
    const candleW = Math.max(1, x.bandwidth());
    const cx = (i: number) => (x(i) ?? 0) + candleW / 2;

    // y-domain spans whatever is drawn: bar highs/lows (candle) or closes
    // (line/area), widened to include any visible overlay.
    const yValues: number[] =
      chartType === 'candle'
        ? bars.flatMap((b) => [b.high, b.low])
        : bars.map((b) => b.close);
    const overlayVals: number[] = [];
    if (showSma) {
      for (const arr of [technicals.sma_20, technicals.sma_50,
        technicals.sma_200]) {
        for (const v of arr) if (v != null) overlayVals.push(v);
      }
    }
    if (showBollinger) {
      for (const arr of [technicals.bb_upper, technicals.bb_lower]) {
        for (const v of arr ?? []) if (v != null) overlayVals.push(v);
      }
    }
    const all = [...yValues, ...overlayVals];
    const lo = min(all) ?? 0;
    const hi = max(all) ?? 1;
    const pad = (hi - lo) * 0.06 || 1;
    const y = scaleLinear()
      .domain([lo - pad, hi + pad])
      .range([innerH, 0])
      .nice();

    const linePath =
      line<Bar>().x((_, i) => cx(i)).y((b) => y(b.close))
        .curve(curveMonotoneX)(bars) ?? '';
    const areaPath =
      area<Bar>().x((_, i) => cx(i)).y0(innerH).y1((b) => y(b.close))
        .curve(curveMonotoneX)(bars) ?? '';

    const overlayPath = (values: (number | null)[]) =>
      line<{ i: number; v: number | null }>()
        .defined((d) => d.v != null && Number.isFinite(d.v))
        .x((d) => cx(d.i))
        .y((d) => y(d.v as number))
        .curve(curveMonotoneX)(values.map((v, i) => ({ i, v }))) ?? '';

    let bollingerArea = '';
    if (showBollinger && technicals.bb_upper && technicals.bb_lower) {
      const upper = technicals.bb_upper;
      const lower = technicals.bb_lower;
      bollingerArea =
        area<number>()
          .defined((i) => upper[i] != null && lower[i] != null)
          .x((i) => cx(i))
          .y0((i) => y(lower[i] as number))
          .y1((i) => y(upper[i] as number))
          .curve(curveMonotoneX)(bars.map((_, i) => i)) ?? '';
    }

    const step = Math.max(1, Math.ceil(bars.length / 6));
    const xTicks = bars
      .map((b, i) => ({ b, i }))
      .filter(({ i }) => i % step === 0)
      .map(({ b, i }) => ({ value: i, offset: cx(i), label: formatDay(b.date) }));
    const yTicks = y
      .ticks(5)
      .map((t) => ({ value: t, offset: y(t), label: t.toFixed(0) }));

    return {
      x, y, cx, candleW, innerW, innerH, linePath, areaPath, overlayPath,
      bollingerArea, xTicks, yTicks,
    };
  }, [bars, technicals, chartType, showSma, showBollinger,
    dims.width, height]);

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
      <ChartFrame width={dims.width} height={height} margin={MARGIN}
        label="Instrument price chart">
        {() => (
          <>
            {g.yTicks.map((t) => (
              <line key={`grid-${t.value}`} x1={0} x2={g.innerW}
                y1={t.offset} y2={t.offset}
                stroke={tokens.color.border} strokeWidth={1} />
            ))}
            <Axis orientation="left" ticks={g.yTicks} />
            <Axis orientation="bottom" ticks={g.xTicks} />

            {showBollinger && g.bollingerArea && (
              <path d={g.bollingerArea} fill={tokens.color.accent}
                fillOpacity={0.08} />
            )}

            {chartType === 'candle' &&
              bars.map((b, i) => {
                const up = b.close >= b.open;
                const color = up ? tokens.color.up : tokens.color.down;
                const bodyTop = Math.min(g.y(b.open), g.y(b.close));
                const bodyH = Math.max(1, Math.abs(g.y(b.close) - g.y(b.open)));
                return (
                  <g key={b.date}
                    opacity={active === null || active === i ? 1 : 0.5}>
                    <line x1={g.cx(i)} x2={g.cx(i)} y1={g.y(b.high)}
                      y2={g.y(b.low)} stroke={color} strokeWidth={1} />
                    <rect x={g.x(i) ?? 0} y={bodyTop} width={g.candleW}
                      height={bodyH} fill={color}
                      rx={Math.min(1, g.candleW / 3)} />
                  </g>
                );
              })}

            {chartType === 'area' && (
              <path d={g.areaPath} fill={tokens.color.accent}
                fillOpacity={0.14} />
            )}
            {chartType !== 'candle' && (
              <path d={g.linePath} fill="none" stroke={tokens.color.accent}
                strokeWidth={1.75} strokeLinejoin="round" />
            )}

            {showSma && (
              <>
                <path d={g.overlayPath(technicals.sma_20)} fill="none"
                  stroke={smaColor[20]} strokeWidth={1.25} />
                <path d={g.overlayPath(technicals.sma_50)} fill="none"
                  stroke={smaColor[50]} strokeWidth={1.25} />
                <path d={g.overlayPath(technicals.sma_200)} fill="none"
                  stroke={smaColor[200]} strokeWidth={1.25} />
              </>
            )}
            {showBollinger && technicals.bb_upper && technicals.bb_lower && (
              <>
                <path d={g.overlayPath(technicals.bb_upper)} fill="none"
                  stroke={tokens.color.accent} strokeWidth={1}
                  strokeDasharray="3 3" />
                <path d={g.overlayPath(technicals.bb_lower)} fill="none"
                  stroke={tokens.color.accent} strokeWidth={1}
                  strokeDasharray="3 3" />
              </>
            )}

            {activeBar && active !== null && (
              <line x1={g.cx(active)} x2={g.cx(active)} y1={0} y2={g.innerH}
                stroke={tokens.color.inkSoft} strokeWidth={1}
                strokeDasharray="3 3" pointerEvents="none" />
            )}

            <rect ref={plotRef} x={0} y={0} width={g.innerW} height={g.innerH}
              fill="transparent" onMouseMove={onMove}
              onMouseLeave={() => setActive(null)} />
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
    </div>
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npx vitest run src/charts/PriceChart.test.tsx` — Expected: PASS.
Run: `npx tsc --noEmit` — Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/charts/PriceChart.tsx frontend/src/charts/PriceChart.test.tsx
git commit -m "feat(frontend): add multi-mode PriceChart with SMA and Bollinger"
```

---

## Task 5: VolumeChart sub-chart

**Files:**
- Create: `frontend/src/charts/VolumeChart.tsx`
- Test: `frontend/src/charts/VolumeChart.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/charts/VolumeChart.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { VolumeChart } from './VolumeChart';
import type { Bar } from '../lib/types';

function makeBars(n: number): Bar[] {
  return Array.from({ length: n }, (_, i) => ({
    date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
    open: 100, high: 101, low: 99, close: i % 2 ? 100.5 : 99.5,
    volume: 1000 + i * 10,
  }));
}

test('renders one volume bar per input bar', () => {
  const { container } = render(<VolumeChart bars={makeBars(15)} />);
  expect(container.querySelectorAll('rect').length).toBe(15);
});

test('renders nothing for empty bars', () => {
  const { container } = render(<VolumeChart bars={[]} />);
  expect(container.querySelector('svg')).toBeNull();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/charts/VolumeChart.test.tsx`
Expected: FAIL — cannot resolve `./VolumeChart`.

- [ ] **Step 3: Create the chart**

Create `frontend/src/charts/VolumeChart.tsx`:

```tsx
import { useMemo } from 'react';
import { scaleBand, scaleLinear } from 'd3-scale';
import { max } from 'd3-array';
import { ChartFrame } from './ChartFrame';
import { Axis } from './Axis';
import { useChartDimensions } from './useChartDimensions';
import { tokens } from '../design/tokens';
import { formatCompact } from '../lib/format';
import type { Bar } from '../lib/types';

const MARGIN = { top: 8, right: 12, bottom: 8, left: 52 };

/** A compact volume sub-chart — one bar per session, colored by direction. */
export function VolumeChart({
  bars, height = 96,
}: {
  bars: Bar[];
  height?: number;
}) {
  const [wrapRef, dims] = useChartDimensions<HTMLDivElement>({
    width: 820, height,
  });

  const g = useMemo(() => {
    const innerW = Math.max(0, dims.width - MARGIN.left - MARGIN.right);
    const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);
    if (bars.length === 0 || innerW <= 0) return null;
    const x = scaleBand<number>()
      .domain(bars.map((_, i) => i))
      .range([0, innerW])
      .padding(0.3);
    const hi = max(bars, (b) => b.volume) ?? 1;
    const y = scaleLinear().domain([0, hi]).range([innerH, 0]).nice();
    const yTicks = y
      .ticks(3)
      .map((t) => ({ value: t, offset: y(t), label: formatCompact(t) }));
    return { x, y, innerW, innerH, yTicks };
  }, [bars, dims.width, height]);

  if (!g) return null;

  return (
    <div ref={wrapRef} className="w-full">
      <ChartFrame width={dims.width} height={height} margin={MARGIN}
        label="Volume chart">
        {() => (
          <>
            <Axis orientation="left" ticks={g.yTicks} />
            {bars.map((b, i) => {
              const up = b.close >= b.open;
              return (
                <rect key={b.date} x={g.x(i) ?? 0} y={g.y(b.volume)}
                  width={Math.max(1, g.x.bandwidth())}
                  height={Math.max(0, g.innerH - g.y(b.volume))}
                  fill={up ? tokens.color.up : tokens.color.down}
                  fillOpacity={0.55} />
              );
            })}
          </>
        )}
      </ChartFrame>
    </div>
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npx vitest run src/charts/VolumeChart.test.tsx` — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/charts/VolumeChart.tsx frontend/src/charts/VolumeChart.test.tsx
git commit -m "feat(frontend): add VolumeChart sub-chart"
```

---

## Task 6: RSIChart sub-chart

**Files:**
- Create: `frontend/src/charts/RSIChart.tsx`
- Test: `frontend/src/charts/RSIChart.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/charts/RSIChart.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { RSIChart } from './RSIChart';

test('renders an RSI line and the 30/50/70 reference levels', () => {
  const values = Array.from({ length: 40 }, (_, i) =>
    i < 14 ? null : 40 + (i % 30),
  );
  const { container } = render(<RSIChart values={values} />);
  // 3 reference lines + 1 RSI path
  expect(container.querySelectorAll('line').length).toBe(3);
  expect(container.querySelectorAll('path').length).toBe(1);
});

test('renders nothing without enough RSI data', () => {
  const { container } = render(<RSIChart values={[null, null, null]} />);
  expect(container.querySelector('svg')).toBeNull();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/charts/RSIChart.test.tsx`
Expected: FAIL — cannot resolve `./RSIChart`.

- [ ] **Step 3: Create the chart**

Create `frontend/src/charts/RSIChart.tsx`:

```tsx
import { useMemo } from 'react';
import { scaleLinear } from 'd3-scale';
import { curveMonotoneX, line } from 'd3-shape';
import { ChartFrame } from './ChartFrame';
import { useChartDimensions } from './useChartDimensions';
import { tokens } from '../design/tokens';

const MARGIN = { top: 8, right: 12, bottom: 8, left: 52 };
const LEVELS = [30, 50, 70];

/** A compact RSI sub-chart on a fixed 0–100 scale with reference levels. */
export function RSIChart({
  values, height = 110,
}: {
  values: (number | null)[];
  height?: number;
}) {
  const [wrapRef, dims] = useChartDimensions<HTMLDivElement>({
    width: 820, height,
  });

  const g = useMemo(() => {
    const innerW = Math.max(0, dims.width - MARGIN.left - MARGIN.right);
    const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);
    const defined = values.filter((v) => v != null);
    if (defined.length < 2 || innerW <= 0) return null;
    const x = scaleLinear()
      .domain([0, values.length - 1])
      .range([0, innerW]);
    const y = scaleLinear().domain([0, 100]).range([innerH, 0]);
    const path =
      line<{ i: number; v: number | null }>()
        .defined((d) => d.v != null)
        .x((d) => x(d.i))
        .y((d) => y(d.v as number))
        .curve(curveMonotoneX)(values.map((v, i) => ({ i, v }))) ?? '';
    return { x, y, innerW, innerH, path };
  }, [values, dims.width, height]);

  if (!g) return null;

  return (
    <div ref={wrapRef} className="w-full">
      <ChartFrame width={dims.width} height={height} margin={MARGIN}
        label="RSI chart">
        {() => (
          <>
            {LEVELS.map((level) => (
              <g key={level}>
                <line x1={0} x2={g.innerW} y1={g.y(level)} y2={g.y(level)}
                  stroke={tokens.color.border} strokeWidth={1}
                  strokeDasharray={level === 50 ? '2 3' : undefined} />
                <text x={-8} y={g.y(level)} textAnchor="end"
                  dominantBaseline="middle" fontSize={9}
                  fontFamily={tokens.font.mono} fill={tokens.color.inkMute}>
                  {level}
                </text>
              </g>
            ))}
            <path d={g.path} fill="none" stroke={tokens.color.accent}
              strokeWidth={1.5} strokeLinejoin="round" />
          </>
        )}
      </ChartFrame>
    </div>
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npx vitest run src/charts/RSIChart.test.tsx` — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/charts/RSIChart.tsx frontend/src/charts/RSIChart.test.tsx
git commit -m "feat(frontend): add RSIChart sub-chart"
```

---

## Task 7: MACDChart sub-chart

**Files:**
- Create: `frontend/src/charts/MACDChart.tsx`
- Test: `frontend/src/charts/MACDChart.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/charts/MACDChart.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { MACDChart } from './MACDChart';

function ramp(n: number, fromNull: number): (number | null)[] {
  return Array.from({ length: n }, (_, i) =>
    i < fromNull ? null : Math.sin(i / 4),
  );
}

test('renders MACD and signal paths plus histogram bars', () => {
  const macdLine = ramp(40, 25);
  const signal = ramp(40, 25);
  const histogram = ramp(40, 25);
  const { container } = render(
    <MACDChart line={macdLine} signal={signal} histogram={histogram} />,
  );
  expect(container.querySelectorAll('path').length).toBe(2); // macd + signal
  expect(container.querySelectorAll('rect').length).toBe(15); // 40 - 25
});

test('renders nothing without enough data', () => {
  const { container } = render(
    <MACDChart line={[null]} signal={[null]} histogram={[null]} />,
  );
  expect(container.querySelector('svg')).toBeNull();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/charts/MACDChart.test.tsx`
Expected: FAIL — cannot resolve `./MACDChart`.

- [ ] **Step 3: Create the chart**

Create `frontend/src/charts/MACDChart.tsx`:

```tsx
import { useMemo } from 'react';
import { scaleLinear } from 'd3-scale';
import { curveMonotoneX, line } from 'd3-shape';
import { max, min } from 'd3-array';
import { ChartFrame } from './ChartFrame';
import { useChartDimensions } from './useChartDimensions';
import { tokens } from '../design/tokens';
import { smaColor } from './colors';

const MARGIN = { top: 8, right: 12, bottom: 8, left: 52 };

interface MACDChartProps {
  line: (number | null)[];
  signal: (number | null)[];
  histogram: (number | null)[];
  height?: number;
}

/** A compact MACD sub-chart — MACD line, signal line, and histogram bars. */
export function MACDChart({
  line: macdLine, signal, histogram, height = 120,
}: MACDChartProps) {
  const [wrapRef, dims] = useChartDimensions<HTMLDivElement>({
    width: 820, height,
  });

  const g = useMemo(() => {
    const innerW = Math.max(0, dims.width - MARGIN.left - MARGIN.right);
    const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);
    const all = [...macdLine, ...signal, ...histogram]
      .filter((v): v is number => v != null);
    if (all.length < 2 || innerW <= 0) return null;
    const n = macdLine.length;
    const x = scaleLinear().domain([0, n - 1]).range([0, innerW]);
    const extent = Math.max(Math.abs(min(all) ?? 0), Math.abs(max(all) ?? 1));
    const y = scaleLinear()
      .domain([-extent, extent])
      .range([innerH, 0])
      .nice();
    const barW = Math.max(1, (innerW / n) * 0.6);
    const seriesPath = (values: (number | null)[]) =>
      line<{ i: number; v: number | null }>()
        .defined((d) => d.v != null)
        .x((d) => x(d.i))
        .y((d) => y(d.v as number))
        .curve(curveMonotoneX)(values.map((v, i) => ({ i, v }))) ?? '';
    return {
      x, y, innerW, innerH, barW, zero: y(0),
      macdPath: seriesPath(macdLine),
      signalPath: seriesPath(signal),
    };
  }, [macdLine, signal, histogram, dims.width, height]);

  if (!g) return null;

  return (
    <div ref={wrapRef} className="w-full">
      <ChartFrame width={dims.width} height={height} margin={MARGIN}
        label="MACD chart">
        {() => (
          <>
            <line x1={0} x2={g.innerW} y1={g.zero} y2={g.zero}
              stroke={tokens.color.border} strokeWidth={1} />
            {histogram.map((v, i) =>
              v == null ? null : (
                <rect key={i} x={g.x(i) - g.barW / 2}
                  y={Math.min(g.zero, g.y(v))} width={g.barW}
                  height={Math.max(1, Math.abs(g.y(v) - g.zero))}
                  fill={v >= 0 ? tokens.color.up : tokens.color.down}
                  fillOpacity={0.5} />
              ),
            )}
            <path d={g.macdPath} fill="none" stroke={tokens.color.accent}
              strokeWidth={1.5} />
            <path d={g.signalPath} fill="none" stroke={smaColor[50]}
              strokeWidth={1.5} />
          </>
        )}
      </ChartFrame>
    </div>
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npx vitest run src/charts/MACDChart.test.tsx` — Expected: PASS.
Run: `npx tsc --noEmit` — Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/charts/MACDChart.tsx frontend/src/charts/MACDChart.test.tsx
git commit -m "feat(frontend): add MACDChart sub-chart"
```

---

## Task 8: Command palette (⌘K)

**Files:**
- Create: `frontend/src/components/CommandPalette.tsx`
- Modify: `frontend/src/components/AppShell.tsx`
- Modify: `frontend/src/components/AppBar.tsx`
- Test: `frontend/src/components/CommandPalette.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/CommandPalette.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { RouterProvider, createMemoryRouter } from 'react-router-dom';
import { CommandPalette } from './CommandPalette';

function renderPalette(open = true) {
  const onClose = vi.fn();
  const router = createMemoryRouter(
    [{ path: '*', element: <CommandPalette open={open} onClose={onClose} /> }],
    { initialEntries: ['/'] },
  );
  render(<RouterProvider router={router} />);
  return { onClose, router };
}

test('shows destinations when open', () => {
  renderPalette(true);
  expect(screen.getByPlaceholderText(/Search/i)).toBeInTheDocument();
  expect(screen.getByText('Dashboard')).toBeInTheDocument();
});

test('renders nothing when closed', () => {
  renderPalette(false);
  expect(screen.queryByPlaceholderText(/Search/i)).not.toBeInTheDocument();
});

test('typing a ticker offers an instrument destination', () => {
  renderPalette(true);
  fireEvent.change(screen.getByPlaceholderText(/Search/i), {
    target: { value: 'nvda' },
  });
  expect(screen.getByText(/View instrument: NVDA/i)).toBeInTheDocument();
});

test('Escape closes the palette', () => {
  const { onClose } = renderPalette(true);
  fireEvent.keyDown(screen.getByPlaceholderText(/Search/i), { key: 'Escape' });
  expect(onClose).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/components/CommandPalette.test.tsx`
Expected: FAIL — cannot resolve `./CommandPalette`.

- [ ] **Step 3: Create the command palette**

Create `frontend/src/components/CommandPalette.tsx`:

```tsx
import { useMemo, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { spring } from '../design/motion';
import { useReducedMotion } from '../lib/useReducedMotion';

interface Destination {
  label: string;
  hint: string;
  to: string;
}

/** Fixed destinations the palette can always jump to. */
const STATIC_DESTINATIONS: Destination[] = [
  { label: 'Dashboard', hint: 'Home', to: '/' },
  { label: 'Inflation (CPI)', hint: 'Indicator', to: '/economics/CPIAUCSL' },
  { label: 'Unemployment Rate', hint: 'Indicator', to: '/economics/UNRATE' },
  { label: 'Nonfarm Payrolls', hint: 'Indicator', to: '/economics/PAYEMS' },
  { label: 'Real GDP Growth', hint: 'Indicator',
    to: '/economics/A191RL1Q225SBEA' },
  { label: 'Fed Funds Rate', hint: 'Indicator', to: '/economics/FEDFUNDS' },
  { label: '10-Year Treasury', hint: 'Indicator', to: '/economics/DGS10' },
];

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

/** A ⌘K command palette — jump to an instrument, an indicator, or home. */
export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const reduced = useReducedMotion();
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);

  const items = useMemo<Destination[]>(() => {
    const q = query.trim();
    const matches = STATIC_DESTINATIONS.filter((d) =>
      d.label.toLowerCase().includes(q.toLowerCase()),
    );
    if (q) {
      const ticker = q.toUpperCase().replace(/[^A-Z0-9.\-^]/g, '');
      if (ticker) {
        matches.unshift({
          label: `View instrument: ${ticker}`,
          hint: 'Instrument',
          to: `/finance/${ticker}`,
        });
      }
    }
    return matches;
  }, [query]);

  if (!open) return null;

  function go(dest: Destination | undefined) {
    if (!dest) return;
    onClose();
    setQuery('');
    setActive(0);
    navigate(dest.to, { viewTransition: true });
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => Math.min(items.length - 1, a + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      go(items[active]);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center
                 bg-bg/70 pt-[12vh]"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, y: reduced ? 0 : -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={reduced ? { duration: 0 } : spring.gentle}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg overflow-hidden rounded-lg border
                   border-border-strong bg-surface shadow-2xl"
      >
        <input
          autoFocus
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
          onKeyDown={onKeyDown}
          placeholder="Search instruments, indicators…"
          aria-label="Command palette search"
          className="w-full border-b border-border bg-transparent px-4 py-3
                     text-sm text-ink outline-none placeholder:text-ink-mute"
        />
        <ul className="max-h-80 overflow-y-auto py-1">
          {items.length === 0 && (
            <li className="px-4 py-3 text-xs text-ink-mute">No matches.</li>
          )}
          {items.map((dest, i) => (
            <li key={dest.to}>
              <button
                type="button"
                onMouseEnter={() => setActive(i)}
                onClick={() => go(dest)}
                className={`flex w-full items-center justify-between px-4 py-2
                            text-left text-sm transition-colors ${
                              i === active
                                ? 'bg-raised text-ink'
                                : 'text-ink-soft'
                            }`}
              >
                <span>{dest.label}</span>
                <span className="font-mono text-[10px] text-ink-mute uppercase">
                  {dest.hint}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </motion.div>
    </div>
  );
}
```

- [ ] **Step 4: Wire it into the app shell**

REPLACE the entire contents of `frontend/src/components/AppShell.tsx` with:

```tsx
import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { AppBar } from './AppBar';
import { BriefingRibbon } from './BriefingRibbon';
import { CommandPalette } from './CommandPalette';

/** The persistent chrome: app bar + briefing ribbon, with routed content
 *  below, plus the ⌘K command palette. */
export function AppShell({ children }: { children: ReactNode }) {
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="flex min-h-full flex-col bg-bg">
      <AppBar onOpenSearch={() => setSearchOpen(true)} />
      <BriefingRibbon />
      {children}
      <CommandPalette open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  );
}
```

In `frontend/src/components/AppBar.tsx`, change the component to accept and use an `onOpenSearch` prop. REPLACE the entire contents of `frontend/src/components/AppBar.tsx` with:

```tsx
import { formatFullDate } from '../lib/format';

export function AppBar({ onOpenSearch }: { onOpenSearch: () => void }) {
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
        onClick={onOpenSearch}
        className="rounded-md border border-border px-3 py-1.5 text-xs text-ink-soft
                   transition-colors hover:border-border-strong"
      >
        Search <kbd className="ml-1 text-ink-mute">⌘K</kbd>
      </button>
    </header>
  );
}
```

- [ ] **Step 5: Run the tests + type-check**

Run: `npx vitest run src/components/CommandPalette.test.tsx src/components/shell.test.tsx` — Expected: PASS (the existing `shell.test.tsx` still green — `AppShell` renders `AppBar` the same way).
Run: `npx tsc --noEmit` — Expected: no errors.

If `shell.test.tsx` fails because it renders `<AppBar />` directly without the new required `onOpenSearch` prop, update only that render call to `<AppBar onOpenSearch={() => {}} />` — make no other change.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/CommandPalette.tsx frontend/src/components/CommandPalette.test.tsx frontend/src/components/AppShell.tsx frontend/src/components/AppBar.tsx frontend/src/components/shell.test.tsx
git commit -m "feat(frontend): add the command palette"
```

---

## Task 9: ReturnsTable

**Files:**
- Create: `frontend/src/finance/ReturnsTable.tsx`
- Test: `frontend/src/finance/ReturnsTable.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/finance/ReturnsTable.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { ReturnsTable } from './ReturnsTable';
import type { Returns } from '../lib/types';

const returns: Returns = {
  week_1: 1.2, month_1: -3.4, month_3: 8.0, month_6: 12.5,
  ytd: 6.1, year_1: 22.0, year_3: null,
};

test('renders a labeled cell per period', () => {
  render(<ReturnsTable returns={returns} />);
  expect(screen.getByText('1W')).toBeInTheDocument();
  expect(screen.getByText('YTD')).toBeInTheDocument();
  expect(screen.getByText('3Y')).toBeInTheDocument();
  expect(screen.getByText('+1.20%')).toBeInTheDocument();
  expect(screen.getByText('-3.40%')).toBeInTheDocument();
});

test('shows a dash for a missing period', () => {
  render(<ReturnsTable returns={returns} />);
  // 3Y is null
  expect(screen.getByText('—')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/finance/ReturnsTable.test.tsx`
Expected: FAIL — cannot resolve `./ReturnsTable`.

- [ ] **Step 3: Create the component**

Create `frontend/src/finance/ReturnsTable.tsx`:

```tsx
import type { Returns } from '../lib/types';
import { formatPercent } from '../lib/format';
import { trendColor } from '../charts/colors';
import { tokens } from '../design/tokens';

const PERIODS: { key: keyof Returns; label: string }[] = [
  { key: 'week_1', label: '1W' },
  { key: 'month_1', label: '1M' },
  { key: 'month_3', label: '3M' },
  { key: 'month_6', label: '6M' },
  { key: 'ytd', label: 'YTD' },
  { key: 'year_1', label: '1Y' },
  { key: 'year_3', label: '3Y' },
];

/** Total return over standard lookbacks, as a row of compact cells. */
export function ReturnsTable({ returns }: { returns: Returns }) {
  return (
    <div className="grid grid-cols-4 gap-px overflow-hidden rounded-md border
                    border-border bg-border sm:grid-cols-7">
      {PERIODS.map(({ key, label }) => {
        const value = returns[key];
        return (
          <div key={key} className="bg-surface px-3 py-2">
            <div className="font-mono text-[10px] tracking-wide text-ink-mute
                            uppercase">
              {label}
            </div>
            <div
              className="mt-0.5 font-mono text-sm tabular-nums"
              style={{
                color: value == null ? tokens.color.inkMute
                  : trendColor(value),
              }}
            >
              {value == null ? '—' : formatPercent(value)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npx vitest run src/finance/ReturnsTable.test.tsx` — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/finance/ReturnsTable.tsx frontend/src/finance/ReturnsTable.test.tsx
git commit -m "feat(frontend): add the returns table"
```

---

## Task 10: Enriched InstrumentRoute

**Files:**
- Modify: `frontend/src/routes/InstrumentRoute.tsx`
- Modify: `frontend/src/routes/InstrumentRoute.test.tsx`
- Delete: `frontend/src/charts/CandlestickChart.tsx`
- Delete: `frontend/src/charts/CandlestickChart.test.tsx`

- [ ] **Step 1: Rewrite the route test**

REPLACE the entire contents of `frontend/src/routes/InstrumentRoute.test.tsx` with:

```tsx
import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { InstrumentRoute } from './InstrumentRoute';

const bars = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
  open: 100 + i, high: 104 + i, low: 98 + i, close: 102 + i, volume: 1000,
}));

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
    sma_50: bars.map(() => null),
    sma_200: bars.map(() => null),
    rsi: bars.map((_, i) => (i < 14 ? null : 55)),
    macd_line: bars.map((_, i) => (i < 25 ? null : 0.4)),
    macd_signal: bars.map((_, i) => (i < 25 ? null : 0.2)),
    macd_histogram: bars.map((_, i) => (i < 25 ? null : 0.2)),
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

const instrumentFn = vi.fn();
vi.mock('../lib/api', () => ({
  api: { instrument: (s: string, r?: string) => instrumentFn(s, r) },
}));

test('renders the enriched drill-down for a symbol', async () => {
  instrumentFn.mockResolvedValue(instrument);
  renderWithProviders(<InstrumentRoute />, {
    route: '/finance/AAPL',
    path: '/finance/:symbol',
  });
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: 'AAPL' })).toBeInTheDocument(),
  );
  expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
  expect(screen.getByText('Fundamentals')).toBeInTheDocument();
  expect(screen.getByText('Returns')).toBeInTheDocument();
  expect(screen.getByText('RSI (14)')).toBeInTheDocument();
  expect(screen.getByText('MACD')).toBeInTheDocument();
  expect(screen.getByRole('group', { name: 'Timeframe' })).toBeInTheDocument();
});

test('shows an error message when the instrument has no data', async () => {
  instrumentFn.mockRejectedValue(new Error('404'));
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

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/routes/InstrumentRoute.test.tsx`
Expected: FAIL — the route does not yet render the timeframe group / RSI / Returns sections.

- [ ] **Step 3: Rewrite the route**

REPLACE the entire contents of `frontend/src/routes/InstrumentRoute.tsx` with:

```tsx
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion } from 'motion/react';
import { useInstrument } from '../finance/hooks';
import { PriceChart } from '../charts/PriceChart';
import { VolumeChart } from '../charts/VolumeChart';
import { RSIChart } from '../charts/RSIChart';
import { MACDChart } from '../charts/MACDChart';
import {
  ChartTypeToggle,
  TimeframeControl,
} from '../charts/ChartControls';
import type { ChartType, Timeframe } from '../charts/ChartControls';
import { FundamentalsGrid } from '../finance/FundamentalsGrid';
import { StatsRow } from '../finance/StatsRow';
import { ReturnsTable } from '../finance/ReturnsTable';
import { AppShell } from '../components/AppShell';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { spring } from '../design/motion';
import { clsx } from 'clsx';

const SECTION = 'mt-6 font-mono text-xs tracking-widest text-ink-mute uppercase';

function OverlayToggle({
  label, on, onClick,
}: {
  label: string;
  on: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={clsx(
        'rounded-md border px-2 py-0.5 font-mono text-[10px] transition-colors',
        on
          ? 'border-accent text-accent'
          : 'border-border text-ink-mute hover:text-ink',
      )}
    >
      {label}
    </button>
  );
}

export function InstrumentRoute() {
  const { symbol = '' } = useParams();
  const upper = symbol.toUpperCase();
  const [range, setRange] = useState<Timeframe>('1y');
  const [chartType, setChartType] = useState<ChartType>('candle');
  const [showSma, setShowSma] = useState(true);
  const [showBollinger, setShowBollinger] = useState(false);
  const { data, isLoading, isError } = useInstrument(upper, range);

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

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <TimeframeControl value={range} onChange={setRange} />
              <ChartTypeToggle value={chartType} onChange={setChartType} />
              <OverlayToggle label="SMA" on={showSma}
                onClick={() => setShowSma((v) => !v)} />
              <OverlayToggle label="Bollinger" on={showBollinger}
                onClick={() => setShowBollinger((v) => !v)} />
            </div>

            <div
              className="mt-3 rounded-lg border border-border bg-surface p-4"
              style={{ viewTransitionName: 'instrument-hero' }}
            >
              <PriceChart
                bars={data.bars}
                technicals={data.technicals}
                chartType={chartType}
                showSma={showSma}
                showBollinger={showBollinger}
              />
            </div>

            <h2 className={SECTION}>Volume</h2>
            <div className="mt-2 rounded-lg border border-border bg-surface p-3">
              <VolumeChart bars={data.bars} />
            </div>

            <h2 className={SECTION}>RSI (14)</h2>
            <div className="mt-2 rounded-lg border border-border bg-surface p-3">
              <RSIChart values={data.technicals.rsi ?? []} />
            </div>

            <h2 className={SECTION}>MACD</h2>
            <div className="mt-2 rounded-lg border border-border bg-surface p-3">
              <MACDChart
                line={data.technicals.macd_line ?? []}
                signal={data.technicals.macd_signal ?? []}
                histogram={data.technicals.macd_histogram ?? []}
              />
            </div>

            {data.returns && (
              <>
                <h2 className={SECTION}>Returns</h2>
                <div className="mt-2">
                  <ReturnsTable returns={data.returns} />
                </div>
              </>
            )}

            <h2 className={SECTION}>Momentum &amp; Risk</h2>
            <div className="mt-2">
              <StatsRow stats={data.stats} />
            </div>

            <h2 className={SECTION}>Fundamentals</h2>
            <div className="mt-2">
              <FundamentalsGrid profile={data.profile} />
            </div>

            <h2 className={SECTION}>Why this matters</h2>
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

- [ ] **Step 4: Delete the superseded CandlestickChart**

`PriceChart` fully supersedes `CandlestickChart` (its only consumer was `InstrumentRoute`). Delete both files:

```bash
git rm frontend/src/charts/CandlestickChart.tsx frontend/src/charts/CandlestickChart.test.tsx
```

- [ ] **Step 5: Run the tests + type-check + build**

Run: `npx vitest run src/routes/InstrumentRoute.test.tsx` — Expected: PASS.
Run: `npx vitest run` — Expected: every component/unit test green (no stale `CandlestickChart` references).
Run: `npx tsc --noEmit` — Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/InstrumentRoute.tsx frontend/src/routes/InstrumentRoute.test.tsx frontend/src/charts/CandlestickChart.tsx frontend/src/charts/CandlestickChart.test.tsx
git commit -m "feat(frontend): enrich the instrument drill-down with charts and controls"
```

---

## Task 11: End-to-end coverage of the enriched drill-down

**Files:**
- Modify: `frontend/e2e/overview-to-drilldown.spec.ts`

- [ ] **Step 1: Read the existing spec**

Read `frontend/e2e/overview-to-drilldown.spec.ts` to see how it stubs the API and navigates from the Finance overview into an instrument drill-down. It currently stubs `**/api/finance/instrument/**` with an instrument payload.

- [ ] **Step 2: Update the instrument stub and add enriched assertions**

In `frontend/e2e/overview-to-drilldown.spec.ts`, ensure the stubbed instrument payload's `technicals` object includes the enrichment arrays and a `returns` object, so the new sub-charts and table render. Update the instrument fixture so its `technicals` includes (alongside the existing `sma_*`):

```ts
    rsi: bars.map((_, i) => (i < 14 ? null : 55)),
    macd_line: bars.map((_, i) => (i < 26 ? null : 0.4)),
    macd_signal: bars.map((_, i) => (i < 26 ? null : 0.2)),
    macd_histogram: bars.map((_, i) => (i < 26 ? null : 0.2)),
    bb_upper: bars.map((b) => b.close + 5),
    bb_middle: bars.map((b) => b.close),
    bb_lower: bars.map((b) => b.close - 5),
    volume: bars.map(() => 1000),
```

and a sibling `returns` field on the instrument object:

```ts
  returns: {
    week_1: 1.2, month_1: -3.4, month_3: 8.0, month_6: 12.5,
    ytd: 6.1, year_1: 22.0, year_3: null,
  },
```

(If the existing fixture builds `bars` inline rather than via a named array, introduce a `bars` array first so the `technicals` arrays can map over it; keep the existing bar values.)

Then, in the test that navigates into the instrument drill-down, after the existing assertions add:

```ts
  await expect(page.getByRole('group', { name: 'Timeframe' })).toBeVisible();
  await expect(page.getByText('RSI (14)')).toBeVisible();
  await expect(page.getByText('Returns')).toBeVisible();
  await page.getByRole('button', { name: '5Y' }).click();
  await expect(page.getByRole('button', { name: '5Y' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
```

If the test stubs `**/api/finance/instrument/**` with a fixed payload, the `?range=5y` request matches the same glob, so clicking `5Y` re-renders from the same stub — the assertion verifies the control's pressed state.

- [ ] **Step 3: Run the E2E spec**

Run (from `frontend/`): `npx playwright test overview-to-drilldown`
Expected: PASS. If Playwright browsers are not installed, run `npx playwright install chromium` first.

- [ ] **Step 4: Run the full frontend suite + build**

Run: `npx vitest run` — Expected: every test green.
Run: `npm run build` — Expected: `tsc --noEmit` clean, Vite build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/e2e/overview-to-drilldown.spec.ts
git commit -m "test(frontend): cover the enriched instrument drill-down end-to-end"
```

---

## Final Verification

After all 11 tasks:

- [ ] From `frontend/`, run `npx vitest run` — every test green.
- [ ] From `frontend/`, run `npm run build` — clean.
- [ ] From `frontend/`, run `npx playwright test` — all specs green.
- [ ] Dispatch the final holistic code review, then proceed to
      `superpowers:finishing-a-development-branch`.

Then **Plan B — the bento `/finance` domain page** is written and built next,
reusing `PriceChart`, the chart controls, and the chart sub-components from
this plan.

---

## Notes for the Implementer

- **`PriceChart` supersedes `CandlestickChart`.** Do not leave the old file —
  Task 10 deletes it. The shared-element `viewTransitionName: 'instrument-hero'`
  moves to the `PriceChart` card so the watchlist→drill-down morph still works.
- **Optional type fields:** the backend always sends `rsi`/`macd_*`/`bb_*`/
  `volume`/`returns`, but the frontend types them optional so older fixtures stay
  valid. Consumers default with `?? []` and the sub-charts return `null` on too
  little data — both degradation paths are intentional.
- **Sub-charts are static** (no crosshair) by design — `PriceChart` carries the
  interactive crosshair; the volume/RSI/MACD charts are read-at-a-glance. A
  shared crosshair across the stack is a later polish concern, out of scope here.
- **Timeframe switches** use `keepPreviousData` so the page does not flash a
  skeleton when `range` changes.
- **Command palette:** ⌘K (or ⌃K) opens it from anywhere; the AppBar Search
  button also opens it. It navigates to instruments, the six known economic
  indicators, and Home — the `/finance` and `/economics` domain pages are added
  to its destination list in a later plan.
