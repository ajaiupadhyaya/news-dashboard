import { useParams } from 'react-router-dom';
import { motion } from 'motion/react';
import { AppShell } from '../components/AppShell';
import { Breadcrumb } from '../components/Breadcrumb';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { useStrategy, useStrategyTrades } from '../quant/hooks';
import { EquityCurvePanel } from '../quant/EquityCurvePanel';
import { DrawdownPanel } from '../quant/DrawdownPanel';
import { MonthlyReturnsHeatmap } from '../quant/MonthlyReturnsHeatmap';
import { ParameterSweepHeatmap } from '../quant/ParameterSweepHeatmap';
import { WalkforwardWindowsTable } from '../quant/WalkforwardWindowsTable';
import { PositionsTable } from '../quant/PositionsTable';
import { TradesTable } from '../quant/TradesTable';
import { MethodologyPanel } from '../quant/MethodologyPanel';
import { RecomputeButton } from '../quant/RecomputeButton';
import { ApiError } from '../lib/api';
import { spring } from '../design/motion';
import { tokens } from '../design/tokens';

const SECTION = 'mt-6 font-mono text-xs tracking-widest text-ink-mute uppercase';

const CATEGORY_COLOR: Record<string, string> = {
  classic: tokens.color.inkMute,
  alpha: tokens.color.up,
  benchmark: tokens.color.inkSoft,
};

function formatPct(v: number): string {
  const sign = v > 0 ? '+' : '';
  return `${sign}${(v * 100).toFixed(2)}%`;
}

function MetricChip({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-md border border-border bg-surface px-3 py-2">
      <span className="font-mono text-[10px] tracking-wide text-ink-mute uppercase">
        {label}
      </span>
      <span
        className="font-mono text-sm font-semibold tabular-nums"
        style={{ color: color ?? tokens.color.ink }}
      >
        {value}
      </span>
    </div>
  );
}

/** Strategy drill-down page — equity curve, drawdown, trades, methodology, etc. */
export function StrategyRoute() {
  const { slug = '' } = useParams<{ slug: string }>();

  const { data: detail, isLoading, isError, error } = useStrategy(slug);
  const tradesQuery = useStrategyTrades(slug);

  const is404 =
    isError && error instanceof ApiError && (error as ApiError).status === 404;

  const trades = tradesQuery.data?.trades ?? [];
  const nextCursor = tradesQuery.data?.next_cursor ?? null;

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl p-4">
        <Breadcrumb
          trail={[
            { label: 'Dashboard', to: '/' },
            { label: 'Quant Lab', to: '/quant' },
            { label: detail?.name ?? slug },
          ]}
        />

        {isLoading && (
          <div className="mt-4">
            <PanelSkeleton rows={12} />
          </div>
        )}

        {is404 && (
          <p className="mt-8 text-center text-sm text-down">
            Strategy not found.
          </p>
        )}

        {isError && !is404 && (
          <p className="mt-8 text-center text-sm text-down">
            Couldn't load strategy data.
          </p>
        )}

        {detail && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring.gentle}
            className="mt-3"
          >
            {/* Header */}
            <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h1 className="font-mono text-2xl font-semibold text-ink">
                {detail.name}
              </h1>
              <span
                className="font-mono text-xs tracking-wide uppercase"
                style={{ color: CATEGORY_COLOR[detail.category] ?? tokens.color.inkMute }}
              >
                {detail.category}
              </span>
            </header>

            {/* Headline metrics */}
            <div className="mt-3 flex flex-wrap gap-3">
              <MetricChip
                label="Total Return"
                value={formatPct(detail.tear_sheet.total_return)}
                color={
                  detail.tear_sheet.total_return >= 0
                    ? tokens.color.up
                    : tokens.color.down
                }
              />
              <MetricChip
                label="Sharpe"
                value={detail.tear_sheet.sharpe.toFixed(2)}
                color={
                  detail.tear_sheet.sharpe >= 1
                    ? tokens.color.up
                    : detail.tear_sheet.sharpe < 0
                    ? tokens.color.down
                    : tokens.color.inkSoft
                }
              />
              <MetricChip
                label="Max Drawdown"
                value={formatPct(detail.tear_sheet.max_drawdown)}
                color={tokens.color.down}
              />
              <MetricChip
                label="Live Since"
                value={detail.live_start_date ?? '—'}
              />
            </div>

            {/* Equity curve */}
            <h2 className={SECTION}>Equity Curve</h2>
            <div className="mt-2">
              <EquityCurvePanel series={detail.equity_series} />
            </div>

            {/* Drawdown */}
            <h2 className={SECTION}>Drawdown</h2>
            <div className="mt-2">
              <DrawdownPanel series={detail.drawdown_series} />
            </div>

            {/* Monthly returns heatmap */}
            <h2 className={SECTION}>Monthly Returns</h2>
            <div className="mt-2">
              <MonthlyReturnsHeatmap matrix={detail.monthly_returns} />
            </div>

            {/* Parameter sweep */}
            {detail.param_sweep.length > 0 && (
              <>
                <h2 className={SECTION}>Parameter Sweep</h2>
                <div className="mt-2">
                  <ParameterSweepHeatmap
                    sweep={detail.param_sweep}
                    chosen_params={detail.chosen_params}
                  />
                </div>
              </>
            )}

            {/* Walk-forward windows */}
            {detail.walkforward_windows.length > 0 && (
              <>
                <h2 className={SECTION}>Walk-Forward Windows</h2>
                <div className="mt-2">
                  <WalkforwardWindowsTable windows={detail.walkforward_windows} />
                </div>
              </>
            )}

            {/* Current positions */}
            <h2 className={SECTION}>Positions</h2>
            <div className="mt-2">
              <PositionsTable positions={detail.current_positions} />
            </div>

            {/* Trades (paginated) */}
            <h2 className={SECTION}>Trades</h2>
            <div className="mt-2">
              <TradesTable
                trades={trades}
                isLoading={tradesQuery.isLoading}
                isError={tradesQuery.isError}
                nextCursor={nextCursor}
              />
            </div>

            {/* Methodology */}
            <h2 className={SECTION}>Methodology</h2>
            <div className="mt-2">
              <MethodologyPanel detail={detail} />
            </div>

            {/* Recompute */}
            <div className="mt-6">
              <RecomputeButton slug={slug} />
            </div>
          </motion.div>
        )}
      </div>
    </AppShell>
  );
}
