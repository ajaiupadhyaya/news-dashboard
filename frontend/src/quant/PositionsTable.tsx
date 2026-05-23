import type { PositionRow } from '../lib/quant-types';
import { tokens } from '../design/tokens';

interface PositionsTableProps {
  positions: PositionRow[];
}

/**
 * Open positions table.
 * Columns: Symbol, Qty (signed — negative=short in italic red), Avg Cost, Opened At.
 */
export function PositionsTable({ positions }: PositionsTableProps) {
  return (
    <div className="rounded-md border border-border bg-surface overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border">
            {['Symbol', 'Qty', 'Avg Cost', 'Opened At'].map((label) => (
              <th
                key={label}
                className="px-3 py-2 font-mono text-[10px] tracking-wide text-ink-mute uppercase whitespace-nowrap"
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {positions.map((pos, idx) => {
            const isShort = pos.qty < 0;
            return (
              <tr
                key={`${pos.symbol}-${idx}`}
                className="border-b border-border last:border-0 hover:bg-surface-2 transition-colors"
              >
                <td className="px-3 py-2 font-mono text-xs font-semibold text-ink whitespace-nowrap">
                  {pos.symbol}
                </td>
                <td
                  className="px-3 py-2 font-mono text-xs tabular-nums text-right whitespace-nowrap"
                  style={{
                    color: isShort ? tokens.color.down : tokens.color.up,
                    fontStyle: isShort ? 'italic' : 'normal',
                  }}
                  data-testid={isShort ? 'qty-short' : 'qty-long'}
                >
                  {pos.qty > 0 ? `+${pos.qty.toLocaleString('en-US')}` : pos.qty.toLocaleString('en-US')}
                </td>
                <td className="px-3 py-2 font-mono text-xs tabular-nums text-ink-soft text-right whitespace-nowrap">
                  ${pos.avg_cost.toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-ink-mute whitespace-nowrap">
                  {pos.opened_at}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {positions.length === 0 && (
        <div className="px-4 py-6 text-center font-mono text-xs text-ink-mute">
          No open positions
        </div>
      )}
    </div>
  );
}
