import { useState } from 'react';
import { clsx } from 'clsx';
import { useInstrument } from './hooks';
import { PriceChart } from '../charts/PriceChart';
import { ChartTypeToggle, TimeframeControl } from '../charts/ChartControls';
import type { ChartType, Timeframe } from '../charts/ChartControls';
import { PanelSkeleton } from '../components/PanelSkeleton';
import type { WatchlistQuote } from '../lib/types';
import { INDEX_NAMES } from './indexNames';

/** The hero market chart — pick an index, a timeframe, and a chart type.
 *  Bars come from the shared `useInstrument` hook, which keeps the previous
 *  data while a new index or range loads, so the chart never flashes. */
export function MarketChart({ indices }: { indices: WatchlistQuote[] }) {
  const [symbol, setSymbol] = useState(indices[0]?.symbol ?? '^GSPC');
  const [range, setRange] = useState<Timeframe>('1y');
  const [chartType, setChartType] = useState<ChartType>('area');
  const { data, isLoading, isError } = useInstrument(symbol, range);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <div
          role="group"
          aria-label="Index"
          className="flex gap-0.5 rounded-md border border-border bg-raised p-0.5"
        >
          {indices.map((idx) => (
            <button
              key={idx.symbol}
              type="button"
              aria-pressed={idx.symbol === symbol}
              onClick={() => setSymbol(idx.symbol)}
              className={clsx(
                'rounded px-2 py-0.5 font-mono text-[10px] transition-colors',
                idx.symbol === symbol
                  ? 'bg-accent text-bg'
                  : 'text-ink-mute hover:text-ink',
              )}
            >
              {INDEX_NAMES[idx.symbol] ?? idx.symbol}
            </button>
          ))}
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <TimeframeControl value={range} onChange={setRange} />
          <ChartTypeToggle value={chartType} onChange={setChartType} />
        </div>
      </div>

      <div className="mt-3">
        {isLoading && <PanelSkeleton rows={8} />}
        {isError && (
          <p className="py-12 text-center text-sm text-down">
            Couldn't load chart data.
          </p>
        )}
        {!isError && data && (
          <PriceChart
            bars={data.bars}
            technicals={data.technicals}
            chartType={chartType}
            showSma={false}
            showBollinger={false}
            height={420}
          />
        )}
      </div>
    </div>
  );
}
