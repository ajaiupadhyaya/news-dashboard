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
