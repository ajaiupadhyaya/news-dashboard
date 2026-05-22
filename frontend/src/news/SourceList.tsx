import type { NewsArticle } from '../lib/types';

/** The source-diversity readout — distinct outlets and their counts. */
export function SourceList({ articles }: { articles: NewsArticle[] }) {
  const counts = new Map<string, number>();
  for (const article of articles) {
    counts.set(article.source, (counts.get(article.source) ?? 0) + 1);
  }
  const sources = [...counts.entries()].sort((a, b) => b[1] - a[1]);

  if (sources.length === 0) {
    return <p className="text-xs text-ink-mute">No sources available.</p>;
  }
  return (
    <div className="flex flex-wrap gap-2">
      {sources.map(([source, count]) => (
        <div
          key={source}
          className="flex items-center gap-2 rounded-md border border-border
                     bg-surface px-2.5 py-1.5"
        >
          <span className="text-xs text-ink-soft">{source}</span>
          <span className="font-mono text-[10px] tabular-nums text-ink-mute">
            {count}
          </span>
        </div>
      ))}
    </div>
  );
}
