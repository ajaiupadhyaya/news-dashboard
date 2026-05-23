import type { TradeRow } from '../lib/quant-types';
import { tokens } from '../design/tokens';

const SIDE_STYLE: Record<
  TradeRow['side'],
  { color: string; italic: boolean; label: string }
> = {
  buy: { color: tokens.color.up, italic: false, label: 'buy' },
  sell: { color: tokens.color.down, italic: false, label: 'sell' },
  short: { color: tokens.color.down, italic: true, label: 'short' },
  cover: { color: tokens.color.up, italic: true, label: 'cover' },
};

const PHASE_COLOR: Record<TradeRow['phase'], string> = {
  backtest: tokens.color.inkMute,
  forward: tokens.color.ink,
};

interface TradesTableProps {
  trades: TradeRow[];
  isLoading?: boolean;
  isError?: boolean;
  nextCursor?: string | null;
  onLoadMore?: () => void;
}

/**
 * Strategy trades table.
 * Columns: Date, Symbol, Side (color-coded chip), Qty, Price, Notional, Phase.
 * Accepts pre-fetched trades via props so the consuming route can call the hook
 * (keeps the component easy to test without mocking TanStack Query).
 */
export function TradesTable({
  trades,
  isLoading = false,
  isError = false,
  nextCursor = null,
  onLoadMore,
}: TradesTableProps) {
  if (isLoading) {
    return (
      <div className="rounded-md border border-border bg-surface px-4 py-6 text-center font-mono text-xs text-ink-mute">
        Loading…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-md border border-border bg-surface px-4 py-6 text-center font-mono text-xs text-down">
        Failed to load trades.
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border bg-surface">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-border">
              {['Date', 'Symbol', 'Side', 'Qty', 'Price', 'Notional', 'Phase'].map((label) => (
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
            {trades.map((trade, idx) => {
              const side = SIDE_STYLE[trade.side];
              return (
                <tr
                  key={trade.id ?? `${trade.date}-${trade.symbol}-${idx}`}
                  className="border-b border-border last:border-0 hover:bg-surface-2 transition-colors"
                >
                  <td className="px-3 py-2 font-mono text-xs text-ink-mute tabular-nums whitespace-nowrap">
                    {trade.date}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs font-semibold text-ink whitespace-nowrap">
                    {trade.symbol}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className="font-mono text-xs tracking-wide"
                      style={{
                        color: side.color,
                        fontStyle: side.italic ? 'italic' : 'normal',
                      }}
                    >
                      {side.label}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs tabular-nums text-ink-soft text-right">
                    {trade.qty.toLocaleString('en-US')}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs tabular-nums text-ink-soft text-right whitespace-nowrap">
                    ${trade.price.toLocaleString('en-US', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs tabular-nums text-ink-soft text-right whitespace-nowrap">
                    {trade.notional.toLocaleString('en-US', {
                      style: 'currency',
                      currency: 'USD',
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 0,
                    })}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className="font-mono text-[10px] tracking-wide uppercase"
                      style={{ color: PHASE_COLOR[trade.phase] }}
                    >
                      {trade.phase}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {trades.length === 0 && (
        <div className="px-4 py-6 text-center font-mono text-xs text-ink-mute">
          No trades yet
        </div>
      )}

      {nextCursor !== null && onLoadMore && (
        <div className="border-t border-border px-4 py-3 flex items-center justify-between">
          <span className="font-mono text-xs text-ink-mute">
            Showing {trades.length} most recent trades
          </span>
          <button
            onClick={onLoadMore}
            className="font-mono text-xs text-accent hover:underline"
          >
            Load more
          </button>
        </div>
      )}
    </div>
  );
}
