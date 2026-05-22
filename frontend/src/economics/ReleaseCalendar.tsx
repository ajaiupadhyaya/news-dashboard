import type { ReleaseEvent } from '../lib/types';
import { formatDay } from '../lib/format';

/** A compact list of recent / upcoming economic releases. */
export function ReleaseCalendar({ events }: { events: ReleaseEvent[] }) {
  if (events.length === 0) {
    return (
      <p className="py-2 text-center text-xs text-ink-mute">
        No releases scheduled.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-1">
      {events.slice(0, 6).map((e, i) => (
        <li
          key={`${e.date}-${i}`}
          className="flex items-baseline justify-between gap-3 text-xs"
        >
          <span className="truncate text-ink-soft">{e.release_name}</span>
          <span className="shrink-0 font-mono text-[10px] text-ink-mute">
            {formatDay(e.date)}
          </span>
        </li>
      ))}
    </ul>
  );
}
