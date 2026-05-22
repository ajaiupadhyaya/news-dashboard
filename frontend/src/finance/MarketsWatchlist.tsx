import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import { clsx } from 'clsx';
import type { WatchlistQuote } from '../lib/types';
import { Sparkline } from '../charts/Sparkline';
import { trendColor } from '../charts/colors';
import {
  formatChange, formatCompact, formatPercent, formatPrice,
} from '../lib/format';
import { useWatchlistMutations } from './hooks';
import { spring } from '../design/motion';

type SortKey = 'symbol' | 'price' | 'change' | 'change_pct' | 'volume';
type SortDir = 'asc' | 'desc';

interface Column {
  key: SortKey;
  label: string;
}

const COLUMNS: Column[] = [
  { key: 'symbol', label: 'Symbol' },
  { key: 'price', label: 'Price' },
  { key: 'change', label: 'Change' },
  { key: 'change_pct', label: '% Change' },
  { key: 'volume', label: 'Volume' },
];

/** The full sortable watchlist table for the Finance domain page. */
export function MarketsWatchlist({ quotes }: { quotes: WatchlistQuote[] }) {
  const { add, remove } = useWatchlistMutations();
  const [draft, setDraft] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('change_pct');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const sorted = useMemo(() => {
    const rows = [...quotes];
    rows.sort((a, b) => {
      const cmp =
        sortKey === 'symbol'
          ? a.symbol.localeCompare(b.symbol)
          : (a[sortKey] as number) - (b[sortKey] as number);
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return rows;
  }, [quotes, sortKey, sortDir]);

  function onSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'symbol' ? 'asc' : 'desc');
    }
  }

  function onAdd(e: FormEvent) {
    e.preventDefault();
    const symbol = draft.trim().toUpperCase();
    if (!symbol) return;
    add.mutate(symbol);
    setDraft('');
  }

  return (
    <div>
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-border">
            {COLUMNS.map((col, i) => (
              <th
                key={col.key}
                scope="col"
                aria-sort={
                  sortKey === col.key
                    ? sortDir === 'asc'
                      ? 'ascending'
                      : 'descending'
                    : undefined
                }
                className={clsx('px-2 py-1.5', i === 0 ? 'text-left' : 'text-right')}
              >
                <button
                  type="button"
                  onClick={() => onSort(col.key)}
                  className={clsx(
                    'font-mono text-[10px] tracking-widest uppercase',
                    'transition-colors',
                    sortKey === col.key
                      ? 'text-accent'
                      : 'text-ink-mute hover:text-ink',
                  )}
                >
                  {col.label}
                  {sortKey === col.key && (
                    <span aria-hidden="true">
                      {sortDir === 'asc' ? ' ↑' : ' ↓'}
                    </span>
                  )}
                </button>
              </th>
            ))}
            <th scope="col" className="px-2 py-1.5 text-right">
              <span className="font-mono text-[10px] tracking-widest text-ink-mute uppercase">
                Trend
              </span>
            </th>
            <th scope="col" aria-label="Actions" className="w-8" />
          </tr>
        </thead>
        <tbody>
          <AnimatePresence initial={false}>
            {sorted.map((q) => (
              <motion.tr
                key={q.symbol}
                layout
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={spring.snappy}
                className="group border-b border-border transition-colors hover:bg-raised"
              >
                <td className="px-2 py-1.5">
                  <Link
                    to={`/finance/${encodeURIComponent(q.symbol)}`}
                    viewTransition
                    className="font-mono text-xs font-medium text-ink transition-colors hover:text-accent"
                  >
                    {q.symbol}
                  </Link>
                </td>
                <td className="px-2 py-1.5 text-right font-mono text-xs tabular-nums text-ink">
                  {formatPrice(q.price)}
                </td>
                <td
                  className="px-2 py-1.5 text-right font-mono text-xs tabular-nums"
                  style={{ color: trendColor(q.change) }}
                >
                  {formatChange(q.change)}
                </td>
                <td
                  className="px-2 py-1.5 text-right font-mono text-xs tabular-nums"
                  style={{ color: trendColor(q.change_pct) }}
                >
                  {formatPercent(q.change_pct)}
                </td>
                <td className="px-2 py-1.5 text-right font-mono text-xs tabular-nums text-ink-soft">
                  {formatCompact(q.volume)}
                </td>
                <td className="px-2 py-1.5">
                  <div className="flex justify-end">
                    <Sparkline values={q.sparkline} width={72} height={22} />
                  </div>
                </td>
                <td className="px-2 py-1.5 text-right">
                  <button
                    type="button"
                    onClick={() => remove.mutate(q.symbol)}
                    aria-label={`Remove ${q.symbol}`}
                    className="text-ink-mute opacity-0 transition-opacity hover:text-down group-hover:opacity-100"
                  >
                    ✕
                  </button>
                </td>
              </motion.tr>
            ))}
          </AnimatePresence>
        </tbody>
      </table>

      <form onSubmit={onAdd} className="mt-3 flex gap-1">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add symbol…"
          aria-label="Add symbol"
          className="min-w-0 flex-1 rounded-md border border-border bg-raised px-2 py-1 text-xs text-ink uppercase outline-none transition-colors focus:border-accent"
        />
        <button
          type="submit"
          className="rounded-md border border-border px-3 py-1 text-xs text-ink-soft transition-colors hover:border-border-strong"
        >
          Add
        </button>
      </form>
    </div>
  );
}
