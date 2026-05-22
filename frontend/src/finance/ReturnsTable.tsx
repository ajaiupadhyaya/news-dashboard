import type { Returns } from '../lib/types';
import { formatPercent } from '../lib/format';
import { trendColor } from '../charts/colors';
import { tokens } from '../design/tokens';

const PERIODS: { key: keyof Returns; label: string }[] = [
  { key: 'week_1', label: '1W' },
  { key: 'month_1', label: '1M' },
  { key: 'month_3', label: '3M' },
  { key: 'month_6', label: '6M' },
  { key: 'ytd', label: 'YTD' },
  { key: 'year_1', label: '1Y' },
  { key: 'year_3', label: '3Y' },
];

/** Total return over standard lookbacks, as a row of compact cells. */
export function ReturnsTable({ returns }: { returns: Returns }) {
  return (
    <div className="grid grid-cols-4 gap-px overflow-hidden rounded-md border
                    border-border bg-border sm:grid-cols-7">
      {PERIODS.map(({ key, label }) => {
        const value = returns[key];
        return (
          <div key={key} className="bg-surface px-3 py-2">
            <div className="font-mono text-[10px] tracking-wide text-ink-mute
                            uppercase">
              {label}
            </div>
            <div
              className="mt-0.5 font-mono text-sm tabular-nums"
              style={{
                color: value == null ? tokens.color.inkMute
                  : trendColor(value),
              }}
            >
              {value == null ? '—' : formatPercent(value)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
