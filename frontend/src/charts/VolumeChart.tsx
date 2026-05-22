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
