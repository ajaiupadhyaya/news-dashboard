import type { InstrumentStats } from '../lib/types';
import { formatPercent } from '../lib/format';
import { trendColor } from '../charts/colors';
import { tokens } from '../design/tokens';

/** Momentum (1M/3M/6M) and 30-day volatility as compact stat tiles. */
export function StatsRow({ stats }: { stats: InstrumentStats }) {
  const items = [
    { label: '1M', value: stats.momentum_1m, signed: true },
    { label: '3M', value: stats.momentum_3m, signed: true },
    { label: '6M', value: stats.momentum_6m, signed: true },
    { label: 'Vol 30D', value: stats.volatility_30d, signed: false },
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((it) => (
        <div
          key={it.label}
          className="flex flex-col rounded-md border border-border bg-surface
                     px-3 py-2"
        >
          <span className="font-mono text-[10px] tracking-wide text-ink-mute
                           uppercase">
            {it.label}
          </span>
          <span
            className="font-mono text-sm tabular-nums"
            style={{
              color: it.signed ? trendColor(it.value) : tokens.color.ink,
            }}
          >
            {formatPercent(it.value, { sign: it.signed })}
          </span>
        </div>
      ))}
    </div>
  );
}
