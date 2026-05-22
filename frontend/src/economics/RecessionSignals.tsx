import type { RecessionSignal, SignalStatus } from '../lib/types';
import { tokens } from '../design/tokens';

const STATUS_COLOR: Record<SignalStatus, string> = {
  normal: tokens.color.up,
  warning: '#d2a44e',
  alert: tokens.color.down,
};

/** The drill-down's recession-signal composite — one row per signal. */
export function RecessionSignals({ signals }: { signals: RecessionSignal[] }) {
  if (signals.length === 0) {
    return (
      <p className="text-xs text-ink-mute">
        Recession signals are unavailable right now.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {signals.map((s) => (
        <div
          key={s.name}
          className="flex items-start gap-3 rounded-md border border-border
                     bg-surface px-3 py-2"
        >
          <span
            className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
            style={{ background: STATUS_COLOR[s.status] }}
          />
          <div className="flex flex-col">
            <div className="flex items-baseline gap-2">
              <span className="text-sm text-ink">{s.name}</span>
              <span className="font-mono text-xs tabular-nums text-ink-soft">
                {s.value.toFixed(2)}
              </span>
            </div>
            <span className="text-xs text-ink-mute">{s.detail}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
