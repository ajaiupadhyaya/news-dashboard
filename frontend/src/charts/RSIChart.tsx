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
