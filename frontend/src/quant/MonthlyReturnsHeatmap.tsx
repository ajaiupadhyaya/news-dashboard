import { useMemo } from 'react';

const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

interface MonthlyReturnsHeatmapProps {
  /** year string → month number (1–12) → return decimal */
  matrix: Record<string, Record<number, number>>;
}

function cellColor(value: number | undefined): string {
  if (value === undefined || value === null) return 'bg-surface-2';
  if (value > 0) {
    // green tint, scaling 0→faint, 0.1→full
    const intensity = Math.min(1, value / 0.10);
    const alpha = 0.15 + intensity * 0.75;
    return `rgba(34, 197, 94, ${alpha.toFixed(2)})`;
  }
  // red tint, scaling 0→faint, -0.1→full
  const intensity = Math.min(1, Math.abs(value) / 0.10);
  const alpha = 0.15 + intensity * 0.75;
  return `rgba(239, 68, 68, ${alpha.toFixed(2)})`;
}

function formatPct(v: number): string {
  const sign = v > 0 ? '+' : '';
  return `${sign}${(v * 100).toFixed(1)}%`;
}

/**
 * Monthly returns heatmap.
 * Rows = years descending (latest at top); columns = Jan–Dec.
 * Green = positive return, red = negative, gray = no data.
 */
export function MonthlyReturnsHeatmap({ matrix }: MonthlyReturnsHeatmapProps) {
  const years = useMemo(
    () =>
      Object.keys(matrix)
        .map(Number)
        .filter((y) => !isNaN(y))
        .sort((a, b) => b - a), // descending
    [matrix],
  );

  if (years.length === 0) {
    return (
      <div className="rounded-md border border-border bg-surface px-4 py-3">
        <h3 className="font-mono text-xs font-semibold tracking-wide text-ink-soft uppercase mb-2">
          Monthly Returns
        </h3>
        <p className="font-mono text-xs text-ink-mute text-center py-4">No monthly data</p>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border bg-surface px-4 py-3">
      <h3 className="font-mono text-xs font-semibold tracking-wide text-ink-soft uppercase mb-3">
        Monthly Returns
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-center" data-testid="monthly-heatmap-table">
          <thead>
            <tr>
              <th className="w-12 py-1 pr-2 text-left font-mono text-[10px] text-ink-mute uppercase">
                Year
              </th>
              {MONTH_ABBR.map((m) => (
                <th
                  key={m}
                  className="px-1 py-1 font-mono text-[10px] text-ink-mute uppercase"
                >
                  {m}
                </th>
              ))}
              <th className="pl-2 py-1 font-mono text-[10px] text-ink-mute uppercase">
                Ann.
              </th>
            </tr>
          </thead>
          <tbody>
            {years.map((year) => {
              const yearData = matrix[String(year)] ?? {};
              // Compute annual return from available months (product of (1+r) - 1)
              const monthValues = Object.entries(yearData).map(([, v]) => v);
              const annualReturn = monthValues.length > 0
                ? monthValues.reduce((acc, r) => acc * (1 + r), 1) - 1
                : undefined;

              return (
                <tr key={year} className="hover:bg-surface-2 transition-colors">
                  <td className="pr-2 py-1 text-left font-mono text-[11px] font-semibold text-ink">
                    {year}
                  </td>
                  {Array.from({ length: 12 }, (_, mi) => {
                    const monthNum = mi + 1;
                    // matrix keys might be stored as strings in JSON
                    const value =
                      yearData[monthNum] ??
                      (yearData as Record<string, number>)[String(monthNum)];
                    const bg = cellColor(value);
                    const isColor = bg.startsWith('rgba');
                    return (
                      <td
                        key={monthNum}
                        title={value !== undefined ? `${MONTH_ABBR[mi]} ${year}: ${formatPct(value)}` : 'No data'}
                        className={`px-1 py-1 font-mono text-[9px] tabular-nums ${!isColor ? 'bg-surface-2 text-ink-mute' : 'text-ink'}`}
                        style={isColor ? { backgroundColor: bg } : undefined}
                        data-testid={`cell-${year}-${monthNum}`}
                      >
                        {value !== undefined ? formatPct(value) : '—'}
                      </td>
                    );
                  })}
                  <td
                    className="pl-2 py-1 font-mono text-[10px] tabular-nums font-semibold"
                    style={annualReturn !== undefined
                      ? { color: annualReturn >= 0 ? '#22c55e' : '#ef4444' }
                      : undefined}
                  >
                    {annualReturn !== undefined ? formatPct(annualReturn) : '—'}
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
