import { motion } from 'motion/react';
import type { AssetClass } from '../lib/types';
import { Sparkline } from '../charts/Sparkline';
import { trendColor } from '../charts/colors';
import { formatPercent, formatValue } from '../lib/format';
import { spring } from '../design/motion';

/** The five asset-class mini-cards: Equities, Crypto, Commodities, Rates, FX.
 *  Each shows its representative ticker's value, change, and trend. */
export function AssetClassStrip({
  assetClasses,
}: {
  assetClasses: AssetClass[];
}) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
      {assetClasses.map((ac) => (
        <motion.div
          key={ac.label}
          whileHover={{ y: -2 }}
          transition={spring.snappy}
          className="flex flex-col gap-1 rounded-md border border-border
                     bg-raised px-3 py-2"
        >
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-mono text-[10px] tracking-widest text-ink-mute
                             uppercase">
              {ac.label}
            </span>
            <span
              className="font-mono text-xs tabular-nums"
              style={{ color: trendColor(ac.change_pct) }}
            >
              {formatPercent(ac.change_pct)}
            </span>
          </div>
          <span className="font-mono text-sm tabular-nums text-ink">
            {formatValue(ac.price)}
          </span>
          <Sparkline values={ac.sparkline} width={140} height={28} />
        </motion.div>
      ))}
    </div>
  );
}
