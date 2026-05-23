import type { WalkforwardWindow } from '../lib/quant-types';

interface WalkforwardWindowsTableProps {
  windows: WalkforwardWindow[];
}

function formatRange(start: string, end: string): string {
  return `${start} – ${end}`;
}

function formatParams(params: Record<string, unknown>): string {
  return Object.entries(params)
    .map(([k, v]) => `${k}=${v}`)
    .join(', ');
}

/**
 * Walk-forward validation windows table.
 * One row per window: train range, test range, chosen params, OOS Sharpe.
 */
export function WalkforwardWindowsTable({ windows }: WalkforwardWindowsTableProps) {
  if (windows.length === 0) {
    return (
      <div className="rounded-md border border-border bg-surface px-4 py-3">
        <h3 className="font-mono text-xs font-semibold tracking-wide text-ink-soft uppercase mb-2">
          Walk-forward Windows
        </h3>
        <p className="font-mono text-xs text-ink-mute text-center py-4">
          No walk-forward windows
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border bg-surface px-4 py-3">
      <h3 className="font-mono text-xs font-semibold tracking-wide text-ink-soft uppercase mb-3">
        Walk-forward Windows
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left" data-testid="walkforward-table">
          <thead>
            <tr className="border-b border-border">
              <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-wide text-ink-mute whitespace-nowrap">
                Train Range
              </th>
              <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-wide text-ink-mute whitespace-nowrap">
                Test Range
              </th>
              <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-wide text-ink-mute">
                Chosen Params
              </th>
              <th className="px-3 py-2 font-mono text-[10px] uppercase tracking-wide text-ink-mute whitespace-nowrap text-right">
                OOS Sharpe
              </th>
            </tr>
          </thead>
          <tbody>
            {windows.map((w, idx) => {
              const oosSharpe = w.oos_metrics['sharpe'] ?? w.oos_metrics['oos_sharpe'];
              return (
                <tr
                  key={idx}
                  className="border-b border-border last:border-0 hover:bg-surface-2 transition-colors"
                  data-testid={`window-row-${idx}`}
                >
                  <td className="px-3 py-2 font-mono text-xs text-ink-soft tabular-nums whitespace-nowrap">
                    {formatRange(w.train_start, w.train_end)}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-ink-soft tabular-nums whitespace-nowrap">
                    {formatRange(w.test_start, w.test_end)}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-ink-mute">
                    {formatParams(w.chosen_params)}
                  </td>
                  <td
                    className="px-3 py-2 font-mono text-xs tabular-nums text-right"
                    style={{
                      color:
                        oosSharpe !== undefined
                          ? oosSharpe >= 1
                            ? '#22c55e'
                            : oosSharpe < 0
                              ? '#ef4444'
                              : undefined
                          : undefined,
                    }}
                  >
                    {oosSharpe !== undefined ? oosSharpe.toFixed(2) : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
