import { Link, useParams } from 'react-router-dom';
import { motion } from 'motion/react';
import { useIndicator } from '../economics/hooks';
import { LineChart } from '../charts/LineChart';
import { IndicatorStats } from '../economics/IndicatorStats';
import { RecessionSignals } from '../economics/RecessionSignals';
import { AppShell } from '../components/AppShell';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { spring } from '../design/motion';

export function IndicatorRoute() {
  const { seriesId = '' } = useParams();
  const upper = seriesId.toUpperCase();
  const { data, isLoading, isError } = useIndicator(upper);

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
                {data.name}
              </h1>
              <span className="font-mono text-sm text-ink-soft">
                {data.series_id}
              </span>
            </header>

            <div
              className="mt-4 rounded-lg border border-border bg-surface p-4"
              style={{ viewTransitionName: 'indicator-hero' }}
            >
              <LineChart points={data.series} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Summary
            </h2>
            <div className="mt-2">
              <IndicatorStats detail={data} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Recession Signals
            </h2>
            <div className="mt-2">
              <RecessionSignals signals={data.recession_signals} />
            </div>

            <h2 className="mt-6 font-mono text-xs tracking-widest text-ink-mute
                           uppercase">
              Why this matters
            </h2>
            <p className="mt-2 rounded-md border border-dashed border-border
                          bg-surface px-3 py-3 text-sm text-ink-mute">
              AI-generated context for this indicator arrives in a later phase.
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
