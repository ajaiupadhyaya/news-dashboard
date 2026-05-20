import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import type { WatchlistQuote } from '../lib/types';
import { Sparkline } from '../charts/Sparkline';
import { trendColor } from '../charts/colors';
import { formatPercent, formatPrice } from '../lib/format';
import { useWatchlistMutations } from './hooks';
import { spring } from '../design/motion';

interface WatchlistTableProps {
  quotes: WatchlistQuote[];
}

export function WatchlistTable({ quotes }: WatchlistTableProps) {
  const { add, remove } = useWatchlistMutations();
  const [draft, setDraft] = useState('');

  function onAdd(e: FormEvent) {
    e.preventDefault();
    const symbol = draft.trim().toUpperCase();
    if (!symbol) return;
    add.mutate(symbol);
    setDraft('');
  }

  return (
    <div>
      <ul className="flex flex-col gap-0.5">
        <AnimatePresence initial={false}>
          {quotes.map((q) => (
            <motion.li
              key={q.symbol}
              layout
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={spring.snappy}
            >
              <WatchlistRow
                quote={q}
                onRemove={() => remove.mutate(q.symbol)}
              />
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>

      <form onSubmit={onAdd} className="mt-2 flex gap-1">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add symbol…"
          aria-label="Add symbol"
          className="min-w-0 flex-1 rounded-md border border-border bg-raised px-2 py-1
                     text-xs text-ink uppercase outline-none transition-colors
                     focus:border-accent"
        />
        <button
          type="submit"
          className="rounded-md border border-border px-2 py-1 text-xs text-ink-soft
                     transition-colors hover:border-border-strong"
        >
          Add
        </button>
      </form>
    </div>
  );
}

function WatchlistRow({
  quote,
  onRemove,
}: {
  quote: WatchlistQuote;
  onRemove: () => void;
}) {
  return (
    <div className="group flex items-center gap-2 rounded-md px-2 py-1.5
                    transition-colors hover:bg-raised">
      <Link
        to={`/finance/${encodeURIComponent(quote.symbol)}`}
        className="flex flex-1 items-center gap-3"
      >
        <span className="w-14 font-mono text-xs font-medium text-ink">
          {quote.symbol}
        </span>
        <Sparkline values={quote.sparkline} />
        <span className="ml-auto font-mono text-xs tabular-nums text-ink">
          {formatPrice(quote.price)}
        </span>
        <span
          className="w-16 text-right font-mono text-xs tabular-nums"
          style={{ color: trendColor(quote.change_pct) }}
        >
          {formatPercent(quote.change_pct)}
        </span>
      </Link>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${quote.symbol}`}
        className="text-ink-mute opacity-0 transition-opacity hover:text-down
                   group-hover:opacity-100"
      >
        ✕
      </button>
    </div>
  );
}
