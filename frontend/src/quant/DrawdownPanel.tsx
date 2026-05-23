import { useId, useMemo } from 'react';
import { scaleLinear } from 'd3-scale';
import { area, curveMonotoneX, line } from 'd3-shape';
import { min } from 'd3-array';
import type { DrawdownPoint } from '../lib/quant-types';

const MARGIN = { top: 12, right: 14, bottom: 26, left: 54 };
const DEFAULT_HEIGHT = 180;

interface DrawdownPanelProps {
  series: DrawdownPoint[];
  height?: number;
}

/**
 * Underwater equity (drawdown) area chart.
 * Values are always ≤ 0; the fill is a red tint to signal loss.
 */
export function DrawdownPanel({ series, height = DEFAULT_HEIGHT }: DrawdownPanelProps) {
  const rawId = useId();
  const gradientId = `dd-${rawId.replace(/:/g, '')}`;

  const g = useMemo(() => {
    const innerW = Math.max(0, 820 - MARGIN.left - MARGIN.right);
    const innerH = Math.max(0, height - MARGIN.top - MARGIN.bottom);
    if (series.length < 2 || innerW <= 0) return null;

    const x = scaleLinear().domain([0, series.length - 1]).range([0, innerW]);
    const lo = min(series, (p) => p.drawdown) ?? -1;
    // y domain: from slightly below min to 0
    const pad = Math.abs(lo) * 0.08 || 0.01;
    const y = scaleLinear()
      .domain([lo - pad, 0])
      .range([innerH, 0])
      .nice();

    const linePath =
      line<DrawdownPoint>()
        .x((_, i) => x(i))
        .y((p) => y(p.drawdown))
        .curve(curveMonotoneX)(series) ?? '';

    const areaPath =
      area<DrawdownPoint>()
        .x((_, i) => x(i))
        .y0(y(0))
        .y1((p) => y(p.drawdown))
        .curve(curveMonotoneX)(series) ?? '';

    const step = Math.max(1, Math.ceil(series.length / 6));
    const xTicks = series
      .map((p, i) => ({ p, i }))
      .filter(({ i }) => i % step === 0)
      .map(({ p, i }) => ({ value: i, offset: x(i), label: p.date.slice(0, 7) }));

    const yTicks = y
      .ticks(4)
      .map((t) => ({ value: t, offset: y(t), label: `${(t * 100).toFixed(0)}%` }));

    return { x, y, innerW, innerH, linePath, areaPath, xTicks, yTicks };
  }, [series, height]);

  if (!g) {
    return (
      <div className="flex flex-col gap-2 rounded-md border border-border bg-surface px-4 py-3">
        <h3 className="font-mono text-xs font-semibold tracking-wide text-ink-soft uppercase">
          Drawdown
        </h3>
        <p className="font-mono text-xs text-ink-mute py-4 text-center">No drawdown data</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-surface px-4 py-3">
      <h3 className="font-mono text-xs font-semibold tracking-wide text-ink-soft uppercase">
        Drawdown
      </h3>

      <div className="relative w-full" data-testid="drawdown-chart">
        <svg
          width="100%"
          height={height}
          viewBox={`0 0 820 ${height}`}
          preserveAspectRatio="none"
          role="img"
          aria-label="Drawdown chart"
        >
          <g transform={`translate(${MARGIN.left},${MARGIN.top})`}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ef4444" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#ef4444" stopOpacity={0.05} />
              </linearGradient>
            </defs>

            {/* grid lines */}
            {g.yTicks.map((t) => (
              <line
                key={`grid-${t.value}`}
                x1={0}
                x2={g.innerW}
                y1={t.offset}
                y2={t.offset}
                stroke="currentColor"
                strokeOpacity={0.08}
                strokeWidth={1}
              />
            ))}

            {/* zero line */}
            <line
              x1={0}
              x2={g.innerW}
              y1={g.y(0)}
              y2={g.y(0)}
              stroke="currentColor"
              strokeOpacity={0.25}
              strokeWidth={1}
            />

            {/* area fill */}
            <path d={g.areaPath} fill={`url(#${gradientId})`} />

            {/* line stroke */}
            <path
              d={g.linePath}
              fill="none"
              stroke="#ef4444"
              strokeWidth={1.5}
              strokeLinejoin="round"
            />

            {/* x-axis labels */}
            {g.xTicks.map((t) => (
              <text
                key={`xt-${t.value}`}
                x={t.offset}
                y={g.innerH + 18}
                textAnchor="middle"
                fontSize={9}
                fill="currentColor"
                fillOpacity={0.5}
              >
                {t.label}
              </text>
            ))}

            {/* y-axis labels */}
            {g.yTicks.map((t) => (
              <text
                key={`yt-${t.value}`}
                x={-6}
                y={t.offset + 4}
                textAnchor="end"
                fontSize={9}
                fill="currentColor"
                fillOpacity={0.5}
              >
                {t.label}
              </text>
            ))}
          </g>
        </svg>
      </div>
    </div>
  );
}
