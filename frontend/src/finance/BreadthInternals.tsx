import type { Breadth, WatchlistQuote } from '../lib/types';
import { BreadthGauge } from './BreadthGauge';
import { trendColor } from '../charts/colors';
import { formatPercent, formatValue } from '../lib/format';

/** Market internals — the advance/decline breadth gauge plus the VIX level.
 *  `vix` is the `^VIX` quote from the markets payload, or undefined. */
export function BreadthInternals({
  breadth, vix,
}: {
  breadth: Breadth;
  vix: WatchlistQuote | undefined;
}) {
  return (
    <div className="flex flex-col gap-4">
      <BreadthGauge breadth={breadth} />
      {vix && (
        <div className="flex items-baseline justify-between border-t
                        border-border pt-3">
          <span className="font-mono text-[10px] tracking-widest text-ink-mute
                           uppercase">
            VIX
          </span>
          <span className="font-mono text-lg tabular-nums text-ink">
            {formatValue(vix.price)}
          </span>
          <span
            className="font-mono text-xs tabular-nums"
            style={{ color: trendColor(vix.change_pct) }}
          >
            {formatPercent(vix.change_pct)}
          </span>
        </div>
      )}
    </div>
  );
}
