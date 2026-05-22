import { Link } from 'react-router-dom';
import type { Mover } from '../lib/types';
import { trendColor } from '../charts/colors';
import { formatPercent, formatPrice } from '../lib/format';

function MoverRow({ mover }: { mover: Mover }) {
  return (
    <Link
      to={`/finance/${encodeURIComponent(mover.symbol)}`}
      viewTransition
      className="flex items-center gap-3 rounded-md px-2 py-1.5
                 transition-colors hover:bg-raised"
    >
      <span className="w-14 font-mono text-xs font-medium text-ink">
        {mover.symbol}
      </span>
      <span className="ml-auto font-mono text-xs tabular-nums text-ink">
        {formatPrice(mover.price)}
      </span>
      <span
        className="w-16 text-right font-mono text-xs tabular-nums"
        style={{ color: trendColor(mover.change_pct) }}
      >
        {formatPercent(mover.change_pct)}
      </span>
    </Link>
  );
}

/** The day's biggest gainers and losers, each linking to its drill-down. */
export function TopMovers({
  gainers, losers,
}: {
  gainers: Mover[];
  losers: Mover[];
}) {
  return (
    <div className="flex flex-col gap-3">
      <section>
        <h3 className="mb-1 font-mono text-[10px] tracking-widest text-up
                       uppercase">
          Gainers
        </h3>
        <div className="flex flex-col gap-0.5">
          {gainers.map((m) => (
            <MoverRow key={m.symbol} mover={m} />
          ))}
        </div>
      </section>
      <section>
        <h3 className="mb-1 font-mono text-[10px] tracking-widest text-down
                       uppercase">
          Losers
        </h3>
        <div className="flex flex-col gap-0.5">
          {losers.map((m) => (
            <MoverRow key={m.symbol} mover={m} />
          ))}
        </div>
      </section>
    </div>
  );
}
