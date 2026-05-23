import type { UniverseHealth } from '../lib/quant-types';

interface UniverseHealthTileProps {
  health: UniverseHealth;
}

/** Small health-status tile — shows bar-cache freshness and last forward step per strategy. */
export function UniverseHealthTile({ health }: UniverseHealthTileProps) {
  const slugs = Object.keys(health.last_forward_step_per_strategy);

  return (
    <div className="flex flex-col gap-3 rounded-md border border-border bg-surface px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] tracking-wide text-ink-mute uppercase">
          Universe Health
        </span>
      </div>

      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-ink-mute w-36 shrink-0">
            Last bar fetched at
          </span>
          <span className="font-mono text-xs text-ink tabular-nums">
            {health.latest_bar_fetched_at ?? '—'}
          </span>
        </div>
      </div>

      {slugs.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="font-mono text-[10px] text-ink-mute tracking-wide uppercase mb-1">
            Last forward step per strategy
          </span>
          {slugs.map((slug) => {
            const value = health.last_forward_step_per_strategy[slug];
            return (
              <div key={slug} className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-ink-soft w-44 truncate shrink-0">
                  {slug}
                </span>
                <span className="font-mono text-xs text-ink tabular-nums">
                  {value ?? '—'}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
