import { Link } from 'react-router-dom';
import type { WatchlistQuote } from '../lib/types';
import { Sparkline } from '../charts/Sparkline';
import { trendColor } from '../charts/colors';
import { formatPercent, formatValue } from '../lib/format';
import { INDEX_NAMES } from './indexNames';

/** The major indices, each row linking to its drill-down. */
export function IndicesGrid({ indices }: { indices: WatchlistQuote[] }) {
  return (
    <ul aria-label="Market indices" className="flex flex-col gap-0.5">
      {indices.map((q) => (
        <li key={q.symbol}>
          <Link
            to={`/finance/${encodeURIComponent(q.symbol)}`}
            viewTransition
            className="flex items-center gap-3 rounded-md px-2 py-1.5
                       transition-colors hover:bg-raised"
          >
            <span className="w-24 font-mono text-xs font-medium text-ink">
              {INDEX_NAMES[q.symbol] ?? q.symbol}
            </span>
            <Sparkline values={q.sparkline} width={64} height={22} />
            <span className="ml-auto font-mono text-xs tabular-nums text-ink">
              {formatValue(q.price)}
            </span>
            <span
              className="w-16 text-right font-mono text-xs tabular-nums"
              style={{ color: trendColor(q.change_pct) }}
            >
              {formatPercent(q.change_pct)}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
