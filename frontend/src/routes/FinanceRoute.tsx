import { AppShell } from '../components/AppShell';
import { Breadcrumb } from '../components/Breadcrumb';
import { BentoGrid, BentoTile } from '../components/BentoGrid';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { useMarkets, useOverview } from '../finance/hooks';
import { AssetClassStrip } from '../finance/AssetClassStrip';
import { MarketChart } from '../finance/MarketChart';
import { BreadthInternals } from '../finance/BreadthInternals';
import { IndicesGrid } from '../finance/IndicesGrid';
import { TopMovers } from '../finance/TopMovers';
import { SectorHeatmap } from '../finance/SectorHeatmap';
import { MarketsWatchlist } from '../finance/MarketsWatchlist';
import { formatUpdated } from '../lib/format';

/** The Finance domain page — a bento grid of market tiles. */
export function FinanceRoute() {
  const { data, isLoading, isError, isStale } = useMarkets();
  const overview = useOverview();
  const vix = data?.indices.find((q) => q.symbol === '^VIX');

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-6xl p-4">
        <div className="flex items-center justify-between gap-3">
          <Breadcrumb
            trail={[{ label: 'Dashboard', to: '/' }, { label: 'Finance' }]}
          />
          {data && (
            <span className="font-mono text-[10px] text-ink-mute">
              {isStale ? 'Stale · ' : ''}
              {formatUpdated(data.updated_at)}
            </span>
          )}
        </div>

        {isLoading && (
          <div className="mt-4">
            <PanelSkeleton rows={12} />
          </div>
        )}

        {isError && (
          <p className="mt-8 text-center text-sm text-down">
            Couldn't load market data.
          </p>
        )}

        {data && (
          <div className="mt-4">
            <BentoGrid>
              <BentoTile title="Asset Classes" colSpan={6}>
                <AssetClassStrip assetClasses={data.asset_classes} />
              </BentoTile>

              <BentoTile title="Market Chart" colSpan={4}>
                <MarketChart indices={data.indices} />
              </BentoTile>

              <BentoTile title="Internals" colSpan={2}>
                <BreadthInternals breadth={data.breadth} vix={vix} />
              </BentoTile>

              <BentoTile title="Indices" colSpan={2}>
                <IndicesGrid indices={data.indices} />
              </BentoTile>

              <BentoTile title="Top Movers" colSpan={2}>
                <TopMovers gainers={data.gainers} losers={data.losers} />
              </BentoTile>

              {/* No tile title — SectorHeatmap renders its own header with a
                  live hover readout. */}
              <BentoTile colSpan={2}>
                <SectorHeatmap sectors={data.sectors} />
              </BentoTile>

              <BentoTile title="Watchlist" colSpan={6}>
                {overview.data ? (
                  <MarketsWatchlist quotes={overview.data.watchlist} />
                ) : (
                  <PanelSkeleton rows={4} />
                )}
              </BentoTile>
            </BentoGrid>
          </div>
        )}
      </div>
    </AppShell>
  );
}
