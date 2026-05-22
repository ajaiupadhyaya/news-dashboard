import { Panel } from '../components/Panel';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { useOverview } from './hooks';
import { WatchlistTable } from './WatchlistTable';
import { BreadthGauge } from './BreadthGauge';
import { SectorHeatmap } from './SectorHeatmap';
import { IndexStrip } from './IndexStrip';

/** The Finance quadrant: indices, watchlist, breadth, and sector heatmap. */
export function FinancePanel() {
  const { data, isLoading, isError, isStale } = useOverview();

  return (
    <Panel
      title="Finance"
      icon="💹"
      href="/finance"
      action={
        data ? (
          <span className="font-mono text-[10px] text-ink-mute">
            {isStale ? 'Stale · ' : ''}
            {formatUpdated(data.updated_at)}
          </span>
        ) : undefined
      }
    >
      {isLoading && <PanelSkeleton rows={6} />}
      {isError && (
        <p className="py-8 text-center text-sm text-down">
          Couldn't load market data.
        </p>
      )}
      {data && (
        <div className="flex flex-col gap-4">
          <IndexStrip indices={data.indices} />
          <WatchlistTable quotes={data.watchlist} />
          <BreadthGauge breadth={data.breadth} />
          <SectorHeatmap sectors={data.sectors} />
        </div>
      )}
    </Panel>
  );
}
