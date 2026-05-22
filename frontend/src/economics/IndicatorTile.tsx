import { Link } from 'react-router-dom';
import type { IndicatorSummary } from '../lib/types';
import { formatIndicatorChange, formatIndicatorValue } from '../lib/econFormat';
import { Sparkline } from '../charts/Sparkline';
import { trendColor } from '../charts/colors';
import { tokens } from '../design/tokens';

const TREND_LABEL: Record<IndicatorSummary['trend'], string> = {
  below: 'below normal',
  in: 'in range',
  above: 'above normal',
};

const TREND_COLOR: Record<IndicatorSummary['trend'], string> = {
  below: tokens.color.down,
  in: tokens.color.inkMute,
  above: tokens.color.up,
};

/** One Economics overview tile — links to the indicator drill-down. */
export function IndicatorTile({ summary }: { summary: IndicatorSummary }) {
  return (
    <Link
      to={`/economics/${summary.series_id}`}
      viewTransition
      className="flex flex-col gap-2 rounded-md border border-border
                 bg-surface px-3 py-2.5 transition-colors hover:border-border-strong"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs text-ink-soft">{summary.name}</span>
        <span
          className="font-mono text-[9px] tracking-wide uppercase"
          style={{ color: TREND_COLOR[summary.trend] }}
        >
          {TREND_LABEL[summary.trend]}
        </span>
      </div>
      <div className="flex items-end justify-between gap-2">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-lg tabular-nums text-ink">
            {formatIndicatorValue(summary.latest, summary.unit)}
          </span>
          <span
            className="font-mono text-xs tabular-nums"
            style={{ color: trendColor(summary.change) }}
          >
            {formatIndicatorChange(summary.change, summary.unit)}
          </span>
        </div>
        <Sparkline values={summary.sparkline} />
      </div>
    </Link>
  );
}
