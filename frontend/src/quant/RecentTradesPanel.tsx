import type { TradeRow } from '../lib/quant-types';
import { tokens } from '../design/tokens';

function formatPct(v: number): string {
  return v.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatNotional(v: number): string {
  return v.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

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

/** Recent trades table — columns: date, strategy, symbol, side, qty, price, notional, phase. */
export function RecentTradesPanel({ trades }: { trades: TradeRow[] }) {
  return (
    <div className="overflow-x-auto rounded-md border border-border bg-surface">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border">
            {['Date', 'Strategy', 'Symbol', 'Side', 'Qty', 'Price', 'Notional', 'Phase'].map(
              (label) => (
                <th
                  key={label}
                  className="px-3 py-2 font-mono text-[10px] tracking-wide text-ink-mute uppercase whitespace-nowrap"
                >
                  {label}
                </th>
              ),
            )}
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
                <td className="px-3 py-2 font-mono text-xs text-ink-soft whitespace-nowrap">
                  {trade.strategy_slug ?? '—'}
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
                  ${formatPct(trade.price)}
                </td>
                <td className="px-3 py-2 font-mono text-xs tabular-nums text-ink-soft text-right whitespace-nowrap">
                  {formatNotional(trade.notional)}
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
      {trades.length === 0 && (
        <div className="px-4 py-6 text-center font-mono text-xs text-ink-mute">
          No trades yet.
        </div>
      )}
    </div>
  );
}
