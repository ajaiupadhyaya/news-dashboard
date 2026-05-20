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
