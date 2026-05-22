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
