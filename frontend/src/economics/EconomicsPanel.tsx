import { Panel } from '../components/Panel';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { useEconomicsOverview } from './hooks';
import { IndicatorTile } from './IndicatorTile';
import { ReleaseCalendar } from './ReleaseCalendar';

/** The Economics quadrant: macro-indicator tiles + a release calendar. */
export function EconomicsPanel() {
  const { data, isLoading, isError, isStale } = useEconomicsOverview();

  return (
    <Panel
      title="Economics"
      icon="📊"
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
          Couldn't load economic data.
        </p>
      )}
      {data && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-2">
            {data.indicators.map((ind) => (
              <IndicatorTile key={ind.series_id} summary={ind} />
            ))}
          </div>
          <div>
            <h3 className="mb-1.5 font-mono text-[10px] tracking-widest
                           text-ink-mute uppercase">
              Release Calendar
            </h3>
            <ReleaseCalendar events={data.calendar} />
          </div>
        </div>
      )}
    </Panel>
  );
}
