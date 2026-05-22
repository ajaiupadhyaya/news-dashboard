import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'motion/react';
import { useInstrument } from '../finance/hooks';
import { PriceChart } from '../charts/PriceChart';
import { VolumeChart } from '../charts/VolumeChart';
import { RSIChart } from '../charts/RSIChart';
import { MACDChart } from '../charts/MACDChart';
import {
  ChartTypeToggle,
  TimeframeControl,
} from '../charts/ChartControls';
import type { ChartType, Timeframe } from '../charts/ChartControls';
import { FundamentalsGrid } from '../finance/FundamentalsGrid';
import { StatsRow } from '../finance/StatsRow';
import { ReturnsTable } from '../finance/ReturnsTable';
import { AppShell } from '../components/AppShell';
import { Breadcrumb } from '../components/Breadcrumb';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { spring } from '../design/motion';
import { clsx } from 'clsx';

const SECTION = 'mt-6 font-mono text-xs tracking-widest text-ink-mute uppercase';

function OverlayToggle({
  label, on, onClick,
}: {
  label: string;
  on: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={clsx(
        'rounded-md border px-2 py-0.5 font-mono text-[10px] transition-colors',
        on
          ? 'border-accent text-accent'
          : 'border-border text-ink-mute hover:text-ink',
      )}
    >
      {label}
    </button>
  );
}

export function InstrumentRoute() {
  const { symbol = '' } = useParams();
  const upper = symbol.toUpperCase();
  const [range, setRange] = useState<Timeframe>('1y');
  const [chartType, setChartType] = useState<ChartType>('candle');
  const [showSma, setShowSma] = useState(true);
  const [showBollinger, setShowBollinger] = useState(false);
  const { data, isLoading, isError } = useInstrument(upper, range);

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl p-4">
        <Breadcrumb
          trail={[
            { label: 'Dashboard', to: '/' },
            { label: 'Finance', to: '/finance' },
            { label: upper },
          ]}
        />

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

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <TimeframeControl value={range} onChange={setRange} />
              <ChartTypeToggle value={chartType} onChange={setChartType} />
              <OverlayToggle label="SMA" on={showSma}
                onClick={() => setShowSma((v) => !v)} />
              <OverlayToggle label="Bollinger" on={showBollinger}
                onClick={() => setShowBollinger((v) => !v)} />
            </div>

            <div
              className="mt-3 rounded-lg border border-border bg-surface p-4"
              style={{ viewTransitionName: 'instrument-hero' }}
            >
              <PriceChart
                bars={data.bars}
                technicals={data.technicals}
                chartType={chartType}
                showSma={showSma}
                showBollinger={showBollinger}
              />
            </div>

            <h2 className={SECTION}>Volume</h2>
            <div className="mt-2 rounded-lg border border-border bg-surface p-3">
              <VolumeChart bars={data.bars} />
            </div>

            <h2 className={SECTION}>RSI (14)</h2>
            <div className="mt-2 rounded-lg border border-border bg-surface p-3">
              <RSIChart values={data.technicals.rsi ?? []} />
            </div>

            <h2 className={SECTION}>MACD</h2>
            <div className="mt-2 rounded-lg border border-border bg-surface p-3">
              <MACDChart
                line={data.technicals.macd_line ?? []}
                signal={data.technicals.macd_signal ?? []}
                histogram={data.technicals.macd_histogram ?? []}
              />
            </div>

            {data.returns && (
              <>
                <h2 className={SECTION}>Returns</h2>
                <div className="mt-2">
                  <ReturnsTable returns={data.returns} />
                </div>
              </>
            )}

            <h2 className={SECTION}>Momentum &amp; Risk</h2>
            <div className="mt-2">
              <StatsRow stats={data.stats} />
            </div>

            <h2 className={SECTION}>Fundamentals</h2>
            <div className="mt-2">
              <FundamentalsGrid profile={data.profile} />
            </div>

            <h2 className={SECTION}>Why this matters</h2>
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
