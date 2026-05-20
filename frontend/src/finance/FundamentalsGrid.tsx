import type { Fundamentals } from '../lib/types';
import { formatCompact, formatPercent, formatPrice } from '../lib/format';

export interface FundamentalCell {
  label: string;
  value: string;
}

/** Build the display cells for a fundamentals profile (pure — testable). */
export function buildFundamentalCells(p: Fundamentals): FundamentalCell[] {
  const fmt = (n: number | null, f: (x: number) => string) =>
    n == null ? '—' : f(n);
  return [
    { label: 'Market Cap', value: formatCompact(p.market_cap) },
    { label: 'P/E', value: fmt(p.pe_ratio, (x) => x.toFixed(1)) },
    { label: 'P/B', value: fmt(p.price_to_book, (x) => x.toFixed(2)) },
    {
      label: 'Div Yield',
      value: fmt(p.dividend_yield, (x) => formatPercent(x, { sign: false })),
    },
    { label: 'Beta', value: fmt(p.beta, (x) => x.toFixed(2)) },
    { label: '52W High', value: fmt(p.week52_high, formatPrice) },
    { label: '52W Low', value: fmt(p.week52_low, formatPrice) },
  ];
}

export function FundamentalsGrid({ profile }: { profile: Fundamentals }) {
  const cells = buildFundamentalCells(profile);
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border
                    border-border bg-border sm:grid-cols-4">
      {cells.map((c) => (
        <div key={c.label} className="bg-surface px-3 py-2">
          <div className="font-mono text-[10px] tracking-wide text-ink-mute
                          uppercase">
            {c.label}
          </div>
          <div className="mt-0.5 font-mono text-sm tabular-nums text-ink">
            {c.value}
          </div>
        </div>
      ))}
    </div>
  );
}
