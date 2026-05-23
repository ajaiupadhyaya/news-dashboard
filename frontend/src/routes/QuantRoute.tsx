import { AppShell } from '../components/AppShell';
import { Breadcrumb } from '../components/Breadcrumb';
import { BentoGrid, BentoTile } from '../components/BentoGrid';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { useQuantOverview } from '../quant/hooks';
import { HeroEquityPanel } from '../quant/HeroEquityPanel';
import { LeaderboardPanel } from '../quant/LeaderboardPanel';
import { StrategyTile } from '../quant/StrategyTile';
import { RecentTradesPanel } from '../quant/RecentTradesPanel';
import { UniverseHealthTile } from '../quant/UniverseHealthTile';
import type { StrategySummary } from '../lib/quant-types';

const CLASSICS: string[] = [
  'sma-crossover',
  'rsi-mean-reversion',
  'cross-sectional-momentum',
  'pairs-trading',
  'bollinger-breakout',
];

const ALPHAS: string[] = [
  'news-sentiment-momentum',
  'macro-regime-overlay',
  'multi-factor-combo',
];

const BENCHMARK = 'buy-hold-spy';

const SECTION_HEADER =
  'mt-6 mb-2 font-mono text-xs tracking-widest text-ink-mute uppercase';

/** The Quant Lab domain page — a bento grid of strategy tiles. */
export function QuantRoute() {
  const { data, isLoading, isError } = useQuantOverview();

  const findSummary = (slug: string): StrategySummary | undefined =>
    data?.leaderboard.find((s) => s.slug === slug);

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-6xl p-4">
        <div className="flex items-center justify-between gap-3">
          <Breadcrumb
            trail={[{ label: 'Dashboard', to: '/' }, { label: 'Quant Lab' }]}
          />
        </div>

        {isLoading && (
          <div className="mt-4">
            <PanelSkeleton rows={12} />
          </div>
        )}

        {isError && (
          <p className="mt-8 text-center text-sm text-down">
            Couldn't load quant data.
          </p>
        )}

        {data && (
          <div className="mt-4">
            <BentoGrid>
              <BentoTile title="Combined Equity" colSpan={6}>
                <HeroEquityPanel series={data.hero_equity} />
              </BentoTile>

              <BentoTile title="Leaderboard" colSpan={6}>
                <LeaderboardPanel entries={data.leaderboard} />
              </BentoTile>
            </BentoGrid>

            {/* Classics section */}
            <h2 className={SECTION_HEADER}>Classics</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {CLASSICS.map((slug) => {
                const summary = findSummary(slug);
                if (!summary) return null;
                return <StrategyTile key={slug} summary={summary} />;
              })}
            </div>

            {/* Alpha section */}
            <h2 className={SECTION_HEADER}>Alpha</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {ALPHAS.map((slug) => {
                const summary = findSummary(slug);
                if (!summary) return null;
                return <StrategyTile key={slug} summary={summary} />;
              })}
            </div>

            {/* Benchmark */}
            <h2 className={SECTION_HEADER}>Benchmark</h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {(() => {
                const summary = findSummary(BENCHMARK);
                if (!summary) return null;
                return <StrategyTile key={BENCHMARK} summary={summary} />;
              })()}
            </div>

            <div className="mt-6">
              <BentoGrid>
                <BentoTile title="Recent Trades" colSpan={6}>
                  <RecentTradesPanel trades={data.recent_trades} />
                </BentoTile>

                <BentoTile title="Universe Health" colSpan={4}>
                  <UniverseHealthTile health={data.universe_health} />
                </BentoTile>
              </BentoGrid>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
