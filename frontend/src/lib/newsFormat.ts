import type { StoryStatus } from './types';

/** Relative time: "just now", "5m ago", "3h ago", "2d ago". Uses floor —
 *  elapsed time, so "1h ago" appears only after a full hour. */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const diffMin = Math.floor((now.getTime() - new Date(iso).getTime()) / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  return `${Math.floor(diffH / 24)}d ago`;
}

/** "1 source" / "12 sources". */
export function formatSourceCount(n: number): string {
  return `${n} source${n === 1 ? '' : 's'}`;
}

const STATUS_LABEL: Record<StoryStatus, string> = {
  surging: 'Surging',
  steady: 'Steady',
  fading: 'Fading',
};

/** Display label for a story's momentum status. */
export function formatStatus(status: StoryStatus): string {
  return STATUS_LABEL[status];
}
