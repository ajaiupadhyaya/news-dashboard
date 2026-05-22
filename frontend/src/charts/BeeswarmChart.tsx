import { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { scaleLinear } from 'd3-scale';
import { extent } from 'd3-array';
import { forceCollide, forceSimulation, forceX, forceY } from 'd3-force';
import type { SimulationNodeDatum } from 'd3-force';
import { useChartDimensions } from './useChartDimensions';
import { tokens } from '../design/tokens';
import { spring } from '../design/motion';
import { useReducedMotion } from '../lib/useReducedMotion';
import type { StoryCluster } from '../lib/types';

const STATUS_COLOR: Record<StoryCluster['status'], string> = {
  surging: tokens.color.up,
  steady: tokens.color.accent,
  fading: tokens.color.inkMute,
};

interface BeeswarmChartProps {
  stories: StoryCluster[];
  height?: number;
  onSelect?: (id: string) => void;
}

interface Node extends SimulationNodeDatum {
  id: string;
  story: StoryCluster;
  r: number;
  color: string;
}

/**
 * The News "momentum field": each story is a circle, sized by source
 * count and positioned left→right by momentum. The force layout is settled
 * synchronously; circles then spring into place and re-flow on refresh.
 */
export function BeeswarmChart({
  stories,
  height = 150,
  onSelect,
}: BeeswarmChartProps) {
  const [wrapRef, dims] = useChartDimensions<HTMLDivElement>({
    width: 360,
    height,
  });
  const [hover, setHover] = useState<Node | null>(null);
  const reduced = useReducedMotion();

  const nodes = useMemo<Node[]>(() => {
    const width = dims.width;
    if (stories.length === 0 || width <= 0) return [];

    const maxSrc = Math.max(...stories.map((s) => s.source_count), 1);
    const radius = scaleLinear()
      .domain([1, maxSrc])
      .range([7, 22])
      .clamp(true);
    const [lo, hi] = extent(stories, (s) => s.momentum) as [number, number];
    const mLo = lo ?? 0;
    const mHi = hi ?? 1;
    const xScale = scaleLinear()
      .domain(mLo === mHi ? [mLo - 1, mHi + 1] : [mLo, mHi])
      .range([26, width - 26]);

    const sim: Node[] = stories.map((s) => ({
      id: s.id,
      story: s,
      r: radius(s.source_count),
      color: STATUS_COLOR[s.status],
      x: xScale(s.momentum),
      y: height / 2,
    }));
    const simulation = forceSimulation<Node>(sim)
      .force('x', forceX<Node>((d) => xScale(d.story.momentum)).strength(0.7))
      .force('y', forceY<Node>(height / 2).strength(0.14))
      .force('collide', forceCollide<Node>((d) => d.r + 1.6))
      .stop();
    for (let i = 0; i < 240; i += 1) simulation.tick();
    return sim;
  }, [stories, dims.width, height]);

  return (
    <div ref={wrapRef} className="relative w-full">
      <svg
        width="100%"
        height={height}
        role="img"
        aria-label="Story momentum field"
      >
        {nodes.map((n) => (
          <motion.circle
            key={n.id}
            role="button"
            tabIndex={0}
            aria-label={n.story.headline}
            r={n.r}
            fill={n.color}
            fillOpacity={hover && hover.id !== n.id ? 0.32 : 0.82}
            stroke={tokens.color.bg}
            strokeWidth={1.5}
            initial={false}
            animate={{ cx: n.x ?? 0, cy: n.y ?? 0 }}
            transition={reduced ? { duration: 0 } : spring.smooth}
            style={{ cursor: 'pointer' }}
            onMouseEnter={() => setHover(n)}
            onMouseLeave={() => setHover(null)}
            onClick={() => onSelect?.(n.id)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') onSelect?.(n.id);
            }}
          />
        ))}
      </svg>
      {hover && (
        <div
          className="pointer-events-none absolute top-1 left-1 max-w-[92%]
                     rounded-md border border-border bg-raised/95 px-2.5 py-1.5
                     shadow-lg"
        >
          <div className="line-clamp-2 text-[11px] text-ink-soft">
            {hover.story.headline}
          </div>
          <div className="mt-0.5 font-mono text-[10px] text-ink-mute">
            {hover.story.source_count} sources · momentum{' '}
            {hover.story.momentum.toFixed(1)}
          </div>
        </div>
      )}
    </div>
  );
}
