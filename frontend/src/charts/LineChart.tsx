import { useId, useMemo, useRef, useState } from 'react';
import type { MouseEvent } from 'react';
import { scaleLinear } from 'd3-scale';
import { area, curveMonotoneX, line } from 'd3-shape';
import { max, min } from 'd3-array';
import { ChartFrame } from './ChartFrame';
import { Axis } from './Axis';
import { useChartDimensions } from './useChartDimensions';
import { tokens } from '../design/tokens';
import { formatDay } from '../lib/format';
import type { IndicatorPoint } from '../lib/types';

const MARGIN = { top: 12, right: 14, bottom: 26, left: 54 };

interface LineChartProps {
  points: IndicatorPoint[];
  height?: number;
}

/** Bespoke time-series area/line chart with a crosshair tooltip. */
export function LineChart({ points, height = 360 }: LineChartProps) {
  const [wrapRef, dims] = useChartDimensions<HTMLDivElement>({
    width: 820,
    height,
  });
  const [active, setActive] = useState<number | null>(null);
  const plotRef = useRef<SVGRectElement>(null);
  const rawId = useId();
  const gradientId = `line-${rawId.replace(/:/g, '')}`;

  const g = useMemo(() => {
    const innerW = Math.max(0, dims.width - MARGIN.left - MARGIN.right);
    const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);
    if (points.length < 2 || innerW <= 0) return null;

    const x = scaleLinear().domain([0, points.length - 1]).range([0, innerW]);
    const lo = min(points, (p) => p.value) ?? 0;
    const hi = max(points, (p) => p.value) ?? 1;
    const pad = (hi - lo) * 0.08 || 1;
    const y = scaleLinear()
      .domain([lo - pad, hi + pad])
      .range([innerH, 0])
      .nice();

    const linePath =
      line<IndicatorPoint>()
        .x((_, i) => x(i))
        .y((p) => y(p.value))
        .curve(curveMonotoneX)(points) ?? '';
    const areaPath =
      area<IndicatorPoint>()
        .x((_, i) => x(i))
        .y0(innerH)
        .y1((p) => y(p.value))
        .curve(curveMonotoneX)(points) ?? '';

    const step = Math.max(1, Math.ceil(points.length / 6));
    const xTicks = points
      .map((p, i) => ({ p, i }))
      .filter(({ i }) => i % step === 0)
      .map(({ p, i }) => ({
        value: i,
        offset: x(i),
        label: formatDay(p.date),
      }));
    const yTicks = y
      .ticks(5)
      .map((t) => ({ value: t, offset: y(t), label: t.toFixed(1) }));

    return { x, y, innerW, innerH, linePath, areaPath, xTicks, yTicks };
  }, [points, dims.width, height]);

  function onMove(e: MouseEvent) {
    if (!g || !plotRef.current || points.length < 2) return;
    const box = plotRef.current.getBoundingClientRect();
    const rel = e.clientX - box.left;
    const i = Math.round((rel / g.innerW) * (points.length - 1));
    setActive(Math.min(points.length - 1, Math.max(0, i)));
  }

  const activePoint = active !== null ? points[active] : null;

  if (!g) return null;

  return (
    <div ref={wrapRef} className="relative w-full">
      <ChartFrame
        width={dims.width}
        height={height}
        margin={MARGIN}
        label="Indicator time-series chart"
      >
        {() => (
          <>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor={tokens.color.accent}
                  stopOpacity={0.26}
                />
                <stop
                  offset="100%"
                  stopColor={tokens.color.accent}
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>

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

            <path d={g.areaPath} fill={`url(#${gradientId})`} />
            <path
              d={g.linePath}
              fill="none"
              stroke={tokens.color.accent}
              strokeWidth={1.75}
              strokeLinejoin="round"
            />

            {activePoint && active !== null && (
              <>
                <line
                  x1={g.x(active)}
                  x2={g.x(active)}
                  y1={0}
                  y2={g.innerH}
                  stroke={tokens.color.inkSoft}
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  pointerEvents="none"
                />
                <circle
                  cx={g.x(active)}
                  cy={g.y(activePoint.value)}
                  r={3.5}
                  fill={tokens.color.accent}
                  pointerEvents="none"
                />
              </>
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

      {activePoint && active !== null && (
        <div
          className="pointer-events-none absolute top-2 rounded-md border
                     border-border bg-raised/95 px-3 py-2 font-mono text-[11px]
                     shadow-lg"
          style={{
            left: Math.max(
              MARGIN.left,
              Math.min(dims.width - 130, MARGIN.left + g.x(active)),
            ),
          }}
        >
          <div className="text-ink-soft">{formatDay(activePoint.date)}</div>
          <div className="mt-0.5 text-ink tabular-nums">
            {activePoint.value.toLocaleString('en-US', {
              maximumFractionDigits: 2,
            })}
          </div>
        </div>
      )}
    </div>
  );
}
