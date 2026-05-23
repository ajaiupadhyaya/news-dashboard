import { useMemo } from 'react';
import { LineChart } from '../charts/LineChart';
import type { EquityPoint } from '../lib/quant-types';
import type { IndicatorPoint } from '../lib/types';

interface EquityCurvePanelProps {
  series: EquityPoint[];
}

/**
 * Equity curve panel for the strategy drill-down page.
 * Renders the backtest portion in a muted blue and the forward (live)
 * portion in the full accent color by layering two LineCharts.
 */
export function EquityCurvePanel({ series }: EquityCurvePanelProps) {
  const { backtestPoints, forwardPoints } = useMemo(() => {
    const bt: IndicatorPoint[] = [];
    const fw: IndicatorPoint[] = [];

    for (const p of series) {
      const ip: IndicatorPoint = { date: p.date, value: p.equity };
      if (p.phase === 'forward') {
        fw.push(ip);
      } else {
        bt.push(ip);
      }
    }

    // Stitch the seam: include the last backtest point in the forward slice
    // so the two paths meet without a visual gap.
    if (bt.length > 0 && fw.length > 0) {
      fw.unshift(bt[bt.length - 1]);
    }

    return { backtestPoints: bt, forwardPoints: fw };
  }, [series]);

  // Determine if we have any forward data at all.
  const hasForward = forwardPoints.length >= 2;
  const hasBacktest = backtestPoints.length >= 2;

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border bg-surface px-4 py-3">
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-xs font-semibold tracking-wide text-ink-soft uppercase">
          Equity Curve
        </h3>
        <div className="flex items-center gap-3 font-mono text-[10px] text-ink-mute">
          <span className="flex items-center gap-1">
            <span
              className="inline-block h-0.5 w-4 rounded"
              style={{ backgroundColor: '#6b7280', opacity: 0.6 }}
            />
            Backtest
          </span>
          {hasForward && (
            <span className="flex items-center gap-1">
              <span className="inline-block h-0.5 w-4 rounded bg-accent" />
              Live
            </span>
          )}
        </div>
      </div>

      {series.length < 2 ? (
        <p className="font-mono text-xs text-ink-mute py-4 text-center">No equity data</p>
      ) : (
        <div className="relative w-full" data-testid="equity-chart-container">
          {/* Backtest layer — rendered first, visually muted via opacity wrapper */}
          {hasBacktest && (
            <div
              style={{ opacity: 0.55 }}
              data-testid="equity-backtest-chart"
            >
              <LineChart points={backtestPoints} />
            </div>
          )}

          {/* Forward layer — rendered on top, full opacity, positioned absolute
              when both layers are present so they overlap on the same axes */}
          {hasForward && hasBacktest && (
            <div
              className="absolute inset-0"
              data-testid="equity-forward-chart"
            >
              <LineChart points={forwardPoints} />
            </div>
          )}

          {/* If only forward data (no backtest), render standalone */}
          {hasForward && !hasBacktest && (
            <div data-testid="equity-forward-chart">
              <LineChart points={forwardPoints} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
