import { useMemo } from 'react';
import { LineChart } from '../charts/LineChart';
import type { HeroEquityPoint } from '../lib/quant-types';
import type { IndicatorPoint } from '../lib/types';

interface HeroEquityPanelProps {
  series: HeroEquityPoint[];
}

/** Combined equity curve panel — wraps LineChart over hero_equity series. */
export function HeroEquityPanel({ series }: HeroEquityPanelProps) {
  const points: IndicatorPoint[] = useMemo(
    () => series.map((p) => ({ date: p.date, value: p.equity })),
    [series],
  );

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-surface px-4 py-3">
      <h3 className="font-mono text-xs font-semibold tracking-wide text-ink-soft uppercase">
        Combined Equity (avg of normalized strategies)
      </h3>
      <LineChart points={points} />
    </div>
  );
}
