import type { Quote } from '../lib/types';
import { formatPercent } from '../lib/format';
import { trendColor } from '../charts/colors';

const SHORT_NAME: Record<string, string> = {
  '^GSPC': 'S&P',
  '^DJI': 'Dow',
  '^IXIC': 'Nasdaq',
  '^RUT': 'Rus2K',
  '^VIX': 'VIX',
};

/** A compact one-line summary of the major indices. */
export function IndexStrip({ indices }: { indices: Quote[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1">
      {indices.map((q) => (
        <div key={q.symbol} className="flex items-baseline gap-1.5">
          <span className="font-mono text-[10px] text-ink-mute">
            {SHORT_NAME[q.symbol] ?? q.symbol}
          </span>
          <span
            className="font-mono text-xs tabular-nums"
            style={{ color: trendColor(q.change_pct) }}
          >
            {formatPercent(q.change_pct)}
          </span>
        </div>
      ))}
    </div>
  );
}
