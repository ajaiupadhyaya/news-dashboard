import { Link, useParams } from 'react-router-dom';
import { motion } from 'motion/react';
import { useInstrument } from '../finance/hooks';
import { CandlestickChart } from '../charts/CandlestickChart';
import { FundamentalsGrid } from '../finance/FundamentalsGrid';
import { StatsRow } from '../finance/StatsRow';
import { AppShell } from '../components/AppShell';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { spring } from '../design/motion';

export function InstrumentRoute() {
  const { symbol = '' } = useParams();
  const upper = symbol.toUpperCase();
  const { data, isLoading, isError } = useInstrument(upper);

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl p-4">
        <Link
          to="/"
          viewTransition
          className="font-mono text-xs text-ink-soft transition-colors
                     hover:text-accent"
        >
          ← Dashboard
        </Link>

        {isLoading && (
          <div className="mt-4">
            <PanelSkeleton rows={8} />
          </div>
        )}

        {isError && (
          <p className="mt-8 text-center text-sm text-down">
            No data available for {upper}.
          </p>
        )}

        {data && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring.gentle}
            className="mt-3"
          >
            <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h1 className="font-mono text-2xl font-semibold text-ink">
                {data.symbol}
              </h1>
              <span className="text-sm text-ink-soft">{data.profile.name}</span>
            </header>

            <div
              className="mt-4 rounded-lg border border-border bg-surface p-4"
              style={{ viewTransitionName: 'instrument-hero' }}
            >
              <CandlestickChart bars={data.bars} technicals={data.technicals} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Momentum &amp; Risk
            </h2>
            <div className="mt-2">
              <StatsRow stats={data.stats} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Fundamentals
            </h2>
            <div className="mt-2">
              <FundamentalsGrid profile={data.profile} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Why this matters
            </h2>
            <p className="mt-2 rounded-md border border-dashed border-border
                          bg-surface px-3 py-3 text-sm text-ink-mute">
              AI-generated context for this instrument arrives in a later phase.
            </p>

            <p className="mt-6 font-mono text-[10px] text-ink-mute">
              {formatUpdated(data.updated_at)}
            </p>
          </motion.div>
        )}
      </div>
    </AppShell>
  );
}
