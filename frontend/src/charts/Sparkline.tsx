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
