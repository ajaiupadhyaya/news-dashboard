import { useNavigate } from 'react-router-dom';
import { Panel } from '../components/Panel';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { BeeswarmChart } from '../charts/BeeswarmChart';
import { useNewsOverview } from './hooks';
import { StoryRow } from './StoryRow';

/** The News quadrant: a story-momentum beeswarm + a top-stories list. */
export function NewsPanel() {
  const { data, isLoading, isError, isStale } = useNewsOverview();
  const navigate = useNavigate();

  return (
    <Panel
      title="News"
      icon="📰"
      action={
        data ? (
          <span className="font-mono text-[10px] text-ink-mute">
            {isStale ? 'Stale · ' : ''}
            {formatUpdated(data.updated_at)}
          </span>
        ) : undefined
      }
    >
      {isLoading && <PanelSkeleton rows={6} />}
      {isError && (
        <p className="py-8 text-center text-sm text-down">
          Couldn't load the news.
        </p>
      )}
      {data && data.stories.length === 0 && (
        <p className="py-8 text-center text-sm text-ink-mute">
          No stories yet — the feed is warming up.
        </p>
      )}
      {data && data.stories.length > 0 && (
        <div className="flex flex-col gap-4">
          <BeeswarmChart
            stories={data.stories}
            onSelect={(id) =>
              navigate(`/news/${id}`, { viewTransition: true })
            }
          />
          <div className="flex flex-col gap-1.5">
            {data.stories.slice(0, 6).map((story) => (
              <StoryRow key={story.id} story={story} />
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}
