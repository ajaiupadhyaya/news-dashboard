import { motion } from 'motion/react';
import type { Breadth } from '../lib/types';
import { tokens } from '../design/tokens';
import { spring } from '../design/motion';

/** Advance/decline breadth as an animated diverging bar. */
export function BreadthGauge({ breadth }: { breadth: Breadth }) {
  const total =
    breadth.advancers + breadth.decliners + breadth.unchanged || 1;
  const adv = (breadth.advancers / total) * 100;
  const unc = (breadth.unchanged / total) * 100;
  const dec = (breadth.decliners / total) * 100;

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] tracking-widest text-ink-mute
                         uppercase">
          Breadth
        </span>
        <span className="font-mono text-xs tabular-nums text-ink">
          {breadth.advance_decline_ratio.toFixed(2)} A/D
        </span>
      </div>
      <div className="mt-1.5 flex h-2 overflow-hidden rounded-full bg-raised">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${adv}%` }}
          transition={spring.smooth}
          style={{ background: tokens.color.up }}
        />
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${unc}%` }}
          transition={spring.smooth}
          style={{ background: tokens.color.flat }}
        />
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${dec}%` }}
          transition={spring.smooth}
          style={{ background: tokens.color.down }}
        />
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px]">
        <span style={{ color: tokens.color.up }}>
          {breadth.advancers} adv
        </span>
        <span style={{ color: tokens.color.down }}>
          {breadth.decliners} dec
        </span>
      </div>
    </div>
  );
}
