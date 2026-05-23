import { useMemo } from 'react';
import type { ParameterSweepCell } from '../lib/quant-types';

interface ParameterSweepHeatmapProps {
  sweep: ParameterSweepCell[];
  chosen_params: Record<string, unknown>;
}

/** Interpolate a red-white-green color from sharpe value. */
function sharpeColor(value: number, minV: number, maxV: number): string {
  if (maxV === minV) return 'rgba(156, 163, 175, 0.3)';
  const norm = (value - minV) / (maxV - minV); // 0..1
  // 0 = red, 0.5 = neutral, 1 = green
  if (norm >= 0.5) {
    const t = (norm - 0.5) * 2;
    return `rgba(34, 197, 94, ${(0.15 + t * 0.75).toFixed(2)})`;
  }
  const t = (0.5 - norm) * 2;
  return `rgba(239, 68, 68, ${(0.15 + t * 0.75).toFixed(2)})`;
}

/**
 * Parameter sweep heatmap.
 * Identifies the two most-varying params in the sweep,
 * builds a 2D grid, and renders a D3-style color heatmap.
 * Marks the chosen_params cell with a star marker.
 */
export function ParameterSweepHeatmap({ sweep, chosen_params }: ParameterSweepHeatmapProps) {
  const grid = useMemo(() => {
    if (sweep.length === 0) return null;

    // Collect distinct values per param key
    const distinctMap = new Map<string, Set<unknown>>();
    for (const cell of sweep) {
      for (const [k, v] of Object.entries(cell.params)) {
        if (!distinctMap.has(k)) distinctMap.set(k, new Set());
        distinctMap.get(k)!.add(v);
      }
    }

    // Sort keys by distinct count descending — pick top 2
    const sorted = [...distinctMap.entries()].sort(
      (a, b) => b[1].size - a[1].size,
    );

    if (sorted.length < 1) return null;

    const paramA = sorted[0][0];
    const paramB = sorted.length >= 2 ? sorted[1][0] : null;

    // Unique values for row/col axes — sort numerically if possible
    function sortedValues(set: Set<unknown>): unknown[] {
      const arr = [...set];
      const allNum = arr.every((v) => typeof v === 'number' || !isNaN(Number(v)));
      if (allNum) return arr.sort((a, b) => Number(a) - Number(b));
      return arr.sort((a, b) => String(a).localeCompare(String(b)));
    }

    const rowVals = sortedValues(distinctMap.get(paramA)!);
    const colVals = paramB ? sortedValues(distinctMap.get(paramB)!) : ['all'];

    // Build 2D accumulator: (rowKey, colKey) → {sum, count}
    type Acc = { sum: number; count: number };
    const acc = new Map<string, Acc>();
    const key = (r: unknown, c: unknown) => `${r}|||${c}`;

    for (const cell of sweep) {
      const rVal = cell.params[paramA];
      const cVal = paramB ? cell.params[paramB] : 'all';
      const k = key(rVal, cVal);
      const existing = acc.get(k) ?? { sum: 0, count: 0 };
      existing.sum += cell.sharpe;
      existing.count += 1;
      acc.set(k, existing);
    }

    // Resolve mean sharpe per cell
    type GridCell = { rowVal: unknown; colVal: unknown; sharpe: number; isChosen: boolean };
    const cells: GridCell[] = [];
    let minSharpe = Infinity;
    let maxSharpe = -Infinity;

    for (const rVal of rowVals) {
      for (const cVal of colVals) {
        const entry = acc.get(key(rVal, cVal));
        const sharpe = entry ? entry.sum / entry.count : NaN;
        if (!isNaN(sharpe)) {
          minSharpe = Math.min(minSharpe, sharpe);
          maxSharpe = Math.max(maxSharpe, sharpe);
        }
        const isChosen =
          String(chosen_params[paramA]) === String(rVal) &&
          (paramB ? String(chosen_params[paramB]) === String(cVal) : true);
        cells.push({ rowVal: rVal, colVal: cVal, sharpe, isChosen });
      }
    }

    return { paramA, paramB, rowVals, colVals, cells, minSharpe, maxSharpe };
  }, [sweep, chosen_params]);

  if (!grid) {
    return (
      <div className="rounded-md border border-border bg-surface px-4 py-3">
        <h3 className="font-mono text-xs font-semibold tracking-wide text-ink-soft uppercase mb-2">
          Parameter Sweep
        </h3>
        <p className="font-mono text-xs text-ink-mute text-center py-4">
          No sweep grid for this strategy
        </p>
      </div>
    );
  }

  const { paramA, paramB, rowVals, colVals, cells, minSharpe, maxSharpe } = grid;

  return (
    <div className="rounded-md border border-border bg-surface px-4 py-3">
      <h3 className="font-mono text-xs font-semibold tracking-wide text-ink-soft uppercase mb-1">
        Parameter Sweep
      </h3>
      <p className="font-mono text-[10px] text-ink-mute mb-3">
        {paramA}
        {paramB ? ` × ${paramB}` : ''}{' '}
        — cell color = mean Sharpe; ★ = chosen params
      </p>

      <div className="overflow-x-auto">
        <table className="border-collapse" data-testid="sweep-heatmap-table">
          <thead>
            <tr>
              {/* top-left corner cell */}
              <th className="px-2 py-1 font-mono text-[10px] text-ink-mute text-right">
                {paramA} ↓ / {paramB ?? ''} →
              </th>
              {colVals.map((c) => (
                <th
                  key={String(c)}
                  className="px-2 py-1 font-mono text-[10px] text-ink-mute text-center whitespace-nowrap"
                >
                  {String(c)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rowVals.map((rVal) => (
              <tr key={String(rVal)}>
                <td className="pr-3 py-0.5 font-mono text-[10px] text-ink-mute text-right whitespace-nowrap">
                  {String(rVal)}
                </td>
                {colVals.map((cVal) => {
                  const cell = cells.find(
                    (c) =>
                      String(c.rowVal) === String(rVal) &&
                      String(c.colVal) === String(cVal),
                  );
                  const sharpe = cell?.sharpe;
                  const isChosen = cell?.isChosen ?? false;
                  const bg =
                    sharpe !== undefined && !isNaN(sharpe)
                      ? sharpeColor(sharpe, minSharpe, maxSharpe)
                      : 'transparent';

                  return (
                    <td
                      key={String(cVal)}
                      data-testid={`sweep-cell-${String(rVal)}-${String(cVal)}`}
                      title={sharpe !== undefined && !isNaN(sharpe) ? `Sharpe: ${sharpe.toFixed(2)}` : 'No data'}
                      className="px-2 py-1 text-center font-mono text-[10px] tabular-nums relative"
                      style={{ backgroundColor: bg }}
                    >
                      {sharpe !== undefined && !isNaN(sharpe)
                        ? sharpe.toFixed(2)
                        : '—'}
                      {isChosen && (
                        <span
                          className="ml-0.5 font-bold"
                          data-testid="chosen-marker"
                          title="Chosen parameters"
                        >
                          ★
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
