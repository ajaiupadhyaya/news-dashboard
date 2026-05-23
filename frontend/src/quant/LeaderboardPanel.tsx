import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { StrategySummary } from '../lib/quant-types';
import { tokens } from '../design/tokens';

type SortKey = 'name' | 'category' | 'total_return' | 'sharpe' | 'max_drawdown' | 'live_since';
type SortDir = 'asc' | 'desc';

function formatPct(v: number): string {
  const sign = v > 0 ? '+' : '';
  return `${sign}${(v * 100).toFixed(2)}%`;
}

const CATEGORY_COLOR: Record<StrategySummary['category'], string> = {
  classic: tokens.color.inkMute,
  alpha: tokens.color.up,
  benchmark: tokens.color.inkSoft,
};

interface Column {
  key: SortKey;
  label: string;
}

const COLUMNS: Column[] = [
  { key: 'name', label: 'Name' },
  { key: 'category', label: 'Category' },
  { key: 'total_return', label: 'Total Return' },
  { key: 'sharpe', label: 'Sharpe' },
  { key: 'max_drawdown', label: 'Max Drawdown' },
  { key: 'live_since', label: 'Live Since' },
];

function compareEntries(a: StrategySummary, b: StrategySummary, key: SortKey, dir: SortDir): number {
  let diff = 0;
  if (key === 'name') {
    diff = a.name.localeCompare(b.name);
  } else if (key === 'category') {
    diff = a.category.localeCompare(b.category);
  } else if (key === 'live_since') {
    const aVal = a.live_since ?? '';
    const bVal = b.live_since ?? '';
    diff = aVal.localeCompare(bVal);
  } else {
    diff = (a[key] as number) - (b[key] as number);
  }
  return dir === 'asc' ? diff : -diff;
}

/** Sortable leaderboard table for all strategy summaries. */
export function LeaderboardPanel({ entries }: { entries: StrategySummary[] }) {
  const [sortKey, setSortKey] = useState<SortKey>('sharpe');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  function handleHeaderClick(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  }

  const sorted = [...entries].sort((a, b) => compareEntries(a, b, sortKey, sortDir));

  const dirIcon = (key: SortKey) => {
    if (key !== sortKey) return null;
    return sortDir === 'asc' ? ' ↑' : ' ↓';
  };

  return (
    <div className="overflow-x-auto rounded-md border border-border bg-surface">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border">
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleHeaderClick(col.key)}
                className="cursor-pointer select-none px-3 py-2 font-mono text-[10px]
                           tracking-wide text-ink-mute uppercase hover:text-ink
                           whitespace-nowrap"
              >
                {col.label}{dirIcon(col.key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((entry) => (
            <tr
              key={entry.slug}
              className="border-b border-border last:border-0 hover:bg-surface-2 transition-colors"
            >
              <td className="px-3 py-2">
                <Link
                  to={`/quant/strategy/${entry.slug}`}
                  className="font-mono text-xs text-accent hover:underline"
                >
                  {entry.name}
                </Link>
              </td>
              <td className="px-3 py-2">
                <span
                  className="font-mono text-[10px] tracking-wide uppercase"
                  style={{ color: CATEGORY_COLOR[entry.category] }}
                >
                  {entry.category}
                </span>
              </td>
              <td className="px-3 py-2 font-mono text-xs tabular-nums"
                style={{ color: entry.total_return >= 0 ? tokens.color.up : tokens.color.down }}
              >
                {formatPct(entry.total_return)}
              </td>
              <td className="px-3 py-2 font-mono text-xs tabular-nums"
                style={{ color: entry.sharpe >= 1 ? tokens.color.up : entry.sharpe < 0 ? tokens.color.down : tokens.color.inkSoft }}
              >
                {entry.sharpe.toFixed(2)}
              </td>
              <td className="px-3 py-2 font-mono text-xs tabular-nums"
                style={{ color: tokens.color.down }}
              >
                {formatPct(entry.max_drawdown)}
              </td>
              <td className="px-3 py-2 font-mono text-xs text-ink-mute tabular-nums">
                {entry.live_since ?? '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
