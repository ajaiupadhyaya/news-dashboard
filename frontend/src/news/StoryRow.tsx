import { Link } from 'react-router-dom';
import type { StoryCluster } from '../lib/types';
import {
  formatRelative,
  formatSourceCount,
  formatStatus,
} from '../lib/newsFormat';
import { tokens } from '../design/tokens';

const STATUS_COLOR: Record<StoryCluster['status'], string> = {
  surging: tokens.color.up,
  steady: tokens.color.accent,
  fading: tokens.color.inkMute,
};

/** One top-stories list item — links to the story drill-down. */
export function StoryRow({ story }: { story: StoryCluster }) {
  return (
    <Link
      to={`/news/${story.id}`}
      viewTransition
      className="flex flex-col gap-1 rounded-md border border-border
                 bg-surface px-3 py-2 transition-colors
                 hover:border-border-strong"
    >
      <span className="line-clamp-2 text-xs text-ink-soft">
        {story.headline}
      </span>
      <div className="flex items-center gap-2 font-mono text-[10px]">
        <span style={{ color: STATUS_COLOR[story.status] }}>
          {formatStatus(story.status)}
        </span>
        <span className="text-ink-mute">·</span>
        <span className="text-ink-mute">
          {formatSourceCount(story.source_count)}
        </span>
        <span className="text-ink-mute">·</span>
        <span className="text-ink-mute">
          {formatRelative(story.latest_published_at)}
        </span>
      </div>
    </Link>
  );
}
