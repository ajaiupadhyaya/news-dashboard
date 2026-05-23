import { useState, useEffect } from 'react';
import { useRecompute, useRunStatus } from './hooks';

interface RecomputeButtonProps {
  slug: string;
}

type UIPhase = 'idle' | 'polling' | 'success' | 'failed';

/**
 * Recompute backtest button with a 4-state machine:
 *   idle → polling → (success | failed) → idle (on click)
 */
export function RecomputeButton({ slug }: RecomputeButtonProps) {
  const [runId, setRunId] = useState<number | null>(null);
  const [phase, setPhase] = useState<UIPhase>('idle');
  const [finishedAt, setFinishedAt] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const recompute = useRecompute(slug);

  // Poll the run status only while we're in the "polling" phase.
  const runStatusQuery = useRunStatus(phase === 'polling' ? runId : null);
  const runStatus = runStatusQuery.data;

  // Derive phase transitions from the run status in an effect to avoid
  // setting state during render.
  useEffect(() => {
    if (phase !== 'polling' || !runStatus) return;
    if (runStatus.status === 'success') {
      setFinishedAt(runStatus.finished_at ?? null);
      setPhase('success');
    } else if (runStatus.status === 'failed') {
      setRunError(runStatus.error ?? 'Unknown error');
      setPhase('failed');
    }
  }, [phase, runStatus]);

  function handleClick() {
    if (phase === 'success' || phase === 'failed') {
      // Reset back to idle.
      setPhase('idle');
      setRunId(null);
      setFinishedAt(null);
      setRunError(null);
      return;
    }

    if (phase === 'idle') {
      recompute.mutate(undefined, {
        onSuccess: (data) => {
          setRunId(data.run_id);
          setPhase('polling');
        },
        onError: () => {
          setRunError('Failed to start recompute');
          setPhase('failed');
        },
      });
    }
  }

  const progress = runStatus?.progress;
  const windowsDone = progress?.windows_done ?? 0;
  const windowsTotal = progress?.windows_total ?? 0;

  let label: string;
  let buttonClass: string;

  if (phase === 'idle') {
    label = 'Recompute backtest';
    buttonClass =
      'rounded border border-border bg-raised px-3 py-1.5 font-mono text-xs text-ink-soft hover:text-ink hover:border-accent transition-colors';
  } else if (phase === 'polling') {
    const progressStr = windowsTotal > 0 ? ` (${windowsDone}/${windowsTotal})` : '';
    label = `Recomputing…${progressStr}`;
    buttonClass =
      'rounded border border-border bg-raised px-3 py-1.5 font-mono text-xs text-ink-mute cursor-wait';
  } else if (phase === 'success') {
    label = `Last recomputed: ${finishedAt ?? '—'}`;
    buttonClass =
      'rounded border border-border bg-raised px-3 py-1.5 font-mono text-xs text-up hover:underline cursor-pointer transition-colors';
  } else {
    // failed
    label = `Recompute failed: ${runError ?? 'Unknown error'}`;
    buttonClass =
      'rounded border border-border bg-raised px-3 py-1.5 font-mono text-xs text-down hover:underline cursor-pointer transition-colors';
  }

  return (
    <button
      onClick={handleClick}
      disabled={phase === 'polling' || recompute.isPending}
      className={buttonClass}
      data-testid="recompute-btn"
      data-phase={phase}
    >
      {label}
    </button>
  );
}
