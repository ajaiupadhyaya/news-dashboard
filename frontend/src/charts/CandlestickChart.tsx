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
