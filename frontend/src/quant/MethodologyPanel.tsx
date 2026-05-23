import type { StrategyDetail } from '../lib/quant-types';

interface MethodologyPanelProps {
  detail: StrategyDetail;
}

/**
 * Methodology panel for a strategy drill-down.
 * Shows the blurb, chosen param chips, cost-model summary, and live/inception dates.
 */
export function MethodologyPanel({ detail }: MethodologyPanelProps) {
  const { cost_model } = detail;

  return (
    <div className="rounded-md border border-border bg-surface px-5 py-4 space-y-4">
      <h2 className="font-mono text-sm font-semibold tracking-wide text-ink uppercase">
        Methodology
      </h2>

      <p className="font-sans text-sm text-ink-soft leading-relaxed">
        {detail.methodology_blurb}
      </p>

      <hr className="border-border" />

      {/* Chosen params chips */}
      {Object.keys(detail.chosen_params).length > 0 && (
        <div>
          <p className="font-mono text-[10px] uppercase tracking-wide text-ink-mute mb-2">
            Parameters
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(detail.chosen_params).map(([key, value]) => (
              <span
                key={key}
                className="inline-flex items-center rounded px-2 py-0.5 font-mono text-xs bg-raised border border-border text-ink-soft"
                data-testid={`param-chip-${key}`}
              >
                {key}={String(value)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Cost model */}
      <div>
        <p className="font-mono text-[10px] uppercase tracking-wide text-ink-mute mb-1">
          Cost model
        </p>
        <p className="font-mono text-xs text-ink-soft" data-testid="cost-model-line">
          Commission: ${cost_model.commission.toFixed(2)} · Slippage:{' '}
          {cost_model.slippage_bps} bps · Short:{' '}
          {cost_model.allow_short ? 'enabled' : 'disabled'}
        </p>
      </div>

      {/* Footer */}
      <p className="font-mono text-[10px] text-ink-mute">
        Live since {detail.live_start_date} · Inception {detail.inception_date}
      </p>
    </div>
  );
}
