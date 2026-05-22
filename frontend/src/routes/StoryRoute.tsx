import { Link, useParams } from 'react-router-dom';
import { motion } from 'motion/react';
import { useStory } from '../news/hooks';
import { StoryTimeline } from '../news/StoryTimeline';
import { SourceList } from '../news/SourceList';
import { StoryRow } from '../news/StoryRow';
import { LineChart } from '../charts/LineChart';
import { AppShell } from '../components/AppShell';
import { PanelSkeleton } from '../components/PanelSkeleton';
import { formatUpdated } from '../lib/format';
import { formatSourceCount, formatStatus } from '../lib/newsFormat';
import { spring } from '../design/motion';
import type { IndicatorPoint } from '../lib/types';

const SECTION = 'mt-6 font-mono text-xs tracking-widest text-ink-mute uppercase';

export function StoryRoute() {
  const { clusterId = '' } = useParams();
  const { data, isLoading, isError } = useStory(clusterId);

  const momentumPoints: IndicatorPoint[] =
    data?.momentum_series.map((p) => ({ date: p.time, value: p.count })) ?? [];

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl p-4">
        <Link
          to="/"
          viewTransition
          className="font-mono text-xs text-ink-soft transition-colors
                     hover:text-accent"
        >
          ← Dashboard
        </Link>

        {isLoading && (
          <div className="mt-4">
            <PanelSkeleton rows={8} />
          </div>
        )}

        {isError && (
          <p className="mt-8 text-center text-sm text-down">
            This story is no longer available.
          </p>
        )}

        {data && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring.gentle}
            className="mt-3"
          >
            <header className="flex flex-col gap-1">
              <h1 className="font-mono text-2xl font-semibold text-ink">
                {data.headline}
              </h1>
              <span className="font-mono text-xs text-ink-soft">
                {formatStatus(data.status)} ·{' '}
                {formatSourceCount(data.source_count)} · {data.article_count}{' '}
                articles
              </span>
            </header>

            <p className="mt-3 text-sm text-ink-soft">{data.summary}</p>

            <div
              className="mt-4 rounded-lg border border-border bg-surface p-4"
              style={{ viewTransitionName: 'story-hero' }}
            >
              {momentumPoints.length >= 2 ? (
                <LineChart points={momentumPoints} height={260} />
              ) : (
                <p className="py-8 text-center text-sm text-ink-mute">
                  Not enough coverage yet to chart momentum.
                </p>
              )}
            </div>

            <h2 className={SECTION}>Development Timeline</h2>
            <div className="mt-3">
              <StoryTimeline articles={data.articles} />
            </div>

            <h2 className={SECTION}>Sources</h2>
            <div className="mt-2">
              <SourceList articles={data.articles} />
            </div>

            {data.related.length > 0 && (
              <>
                <h2 className={SECTION}>Related Stories</h2>
                <div className="mt-2 flex flex-col gap-1.5">
                  {data.related.map((story) => (
                    <StoryRow key={story.id} story={story} />
                  ))}
                </div>
              </>
            )}

            <h2 className={SECTION}>Why this matters</h2>
            <p className="mt-2 rounded-md border border-dashed border-border
                          bg-surface px-3 py-3 text-sm text-ink-mute">
              AI-generated context for this story arrives in a later phase.
            </p>

            <p className="mt-6 font-mono text-[10px] text-ink-mute">
              {formatUpdated(data.updated_at)}
            </p>
          </motion.div>
        )}
      </div>
    </AppShell>
  );
}
