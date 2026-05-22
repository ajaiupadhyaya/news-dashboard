import type { IndicatorDetail } from '../lib/types';
import { formatIndicatorChange, formatIndicatorValue } from '../lib/econFormat';
import { trendColor } from '../charts/colors';
import { tokens } from '../design/tokens';

/** The drill-down's headline summary stats as compact tiles. */
export function IndicatorStats({ detail }: { detail: IndicatorDetail }) {
  const items: { label: string; value: string; color: string }[] = [
    {
      label: 'Latest',
      value: formatIndicatorValue(detail.latest, detail.unit),
      color: tokens.color.ink,
    },
    {
      label: 'Change',
      value: formatIndicatorChange(detail.change, detail.unit),
      color: trendColor(detail.change),
    },
    {
      label: 'YoY',
      value:
        detail.yoy == null
          ? '—'
          : `${detail.yoy > 0 ? '+' : ''}${detail.yoy.toFixed(1)}%`,
      color: detail.yoy == null ? tokens.color.inkMute : trendColor(detail.yoy),
    },
    {
      label: 'Momentum',
      value: `${detail.momentum > 0 ? '+' : ''}${detail.momentum.toFixed(1)}%`,
      color: trendColor(detail.momentum),
    },
    {
      label: 'Range',
      value: `${formatIndicatorValue(detail.range_low, detail.unit)} – ${formatIndicatorValue(detail.range_high, detail.unit)}`,
      color: tokens.color.ink,
    },
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
            style={{ color: it.color }}
          >
            {it.value}
          </span>
        </div>
      ))}
    </div>
  );
}
