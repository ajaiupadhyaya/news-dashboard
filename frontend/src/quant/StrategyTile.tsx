import { Link } from 'react-router-dom';
import type { StrategySummary } from '../lib/quant-types';
import { Sparkline } from '../charts/Sparkline';
import { tokens } from '../design/tokens';

const CATEGORY_LABEL: Record<StrategySummary['category'], string> = {
  classic: 'Classic',
  alpha: 'Alpha',
  benchmark: 'Benchmark',
};

const CATEGORY_COLOR: Record<StrategySummary['category'], string> = {
  classic: tokens.color.inkMute,
  alpha: tokens.color.up,
  benchmark: tokens.color.inkSoft,
};

function formatPct(v: number): string {
  const sign = v > 0 ? '+' : '';
  return `${sign}${(v * 100).toFixed(2)}%`;
}

/** One Quant strategy overview tile — links to the strategy drill-down. */
export function StrategyTile({ summary }: { summary: StrategySummary }) {
  return (
    <Link
      to={`/quant/strategy/${summary.slug}`}
      viewTransition
      className="flex flex-col gap-2 rounded-md border border-border
                 bg-surface px-3 py-2.5 transition-colors hover:border-border-strong"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-semibold text-ink">{summary.name}</span>
        <span
          className="font-mono text-[9px] tracking-wide uppercase shrink-0"
          style={{ color: CATEGORY_COLOR[summary.category] }}
        >
          {CATEGORY_LABEL[summary.category]}
        </span>
      </div>

      <div className="flex items-end justify-between gap-2">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-ink-mute w-24">Total Return</span>
            <span
              className="font-mono text-xs tabular-nums"
              style={{ color: summary.total_return >= 0 ? tokens.color.up : tokens.color.down }}
            >
              {formatPct(summary.total_return)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-ink-mute w-24">Sharpe</span>
            <span
              className="font-mono text-xs tabular-nums"
              style={{ color: summary.sharpe >= 1 ? tokens.color.up : summary.sharpe < 0 ? tokens.color.down : tokens.color.inkSoft }}
            >
              {summary.sharpe.toFixed(2)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-ink-mute w-24">Max Drawdown</span>
            <span
              className="font-mono text-xs tabular-nums"
              style={{ color: tokens.color.down }}
            >
              {formatPct(summary.max_drawdown)}
            </span>
          </div>
        </div>
        <Sparkline values={summary.sparkline.slice(-30)} width={80} height={24} />
      </div>

      <div className="mt-0.5">
        {summary.live_since ? (
          <span className="font-mono text-[9px] text-ink-mute">
            Live since {summary.live_since}
          </span>
        ) : (
          <span className="font-mono text-[9px] text-ink-mute">
            Backtest only
          </span>
        )}
      </div>
    </Link>
  );
}
