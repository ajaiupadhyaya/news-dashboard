import { formatFullDate } from '../lib/format';

export function AppBar({ onOpenSearch }: { onOpenSearch: () => void }) {
  const today = formatFullDate(new Date().toISOString());
  return (
    <header className="flex items-center justify-between border-b border-border
                       bg-surface px-5 py-3">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-sm font-semibold tracking-widest text-ink">
          NMD
        </span>
        <span className="text-xs text-ink-mute">{today}</span>
      </div>
      <button
        type="button"
        onClick={onOpenSearch}
        className="rounded-md border border-border px-3 py-1.5 text-xs text-ink-soft
                   transition-colors hover:border-border-strong"
      >
        Search <kbd className="ml-1 text-ink-mute">⌘K</kbd>
      </button>
    </header>
  );
}
