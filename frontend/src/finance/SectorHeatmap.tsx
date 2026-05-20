import { useState } from 'react';
import { motion } from 'motion/react';
import type { SectorChange } from '../lib/types';
import { heatColor } from '../charts/colors';
import { formatPercent } from '../lib/format';
import { spring } from '../design/motion';

/** Sector performance as a heat grid; hovering a cell shows its detail. */
export function SectorHeatmap({ sectors }: { sectors: SectorChange[] }) {
  const [hover, setHover] = useState<SectorChange | null>(null);

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[10px] tracking-widest text-ink-mute
                         uppercase">
          Sectors
        </span>
        <span className="h-4 font-mono text-[10px] text-ink-soft">
          {hover ? `${hover.name} ${formatPercent(hover.change_pct)}` : ''}
        </span>
      </div>
      <div className="mt-1.5 grid grid-cols-4 gap-1">
        {sectors.map((s) => (
          <motion.div
            key={s.symbol}
            whileHover={{ scale: 1.06, zIndex: 1 }}
            transition={spring.snappy}
            onHoverStart={() => setHover(s)}
            onHoverEnd={() => setHover(null)}
            className="flex aspect-[5/3] flex-col justify-between rounded-sm p-1.5"
            style={{ background: heatColor(s.change_pct) }}
          >
            <span className="font-mono text-[9px] font-medium text-ink">
              {s.symbol}
            </span>
            <span className="font-mono text-[10px] tabular-nums text-ink">
              {formatPercent(s.change_pct, { sign: false })}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
