import type { NewsArticle } from '../lib/types';
import { formatRelative } from '../lib/newsFormat';

/** The development timeline — every source article, oldest-first. */
export function StoryTimeline({ articles }: { articles: NewsArticle[] }) {
  if (articles.length === 0) {
    return (
      <p className="text-xs text-ink-mute">No source articles available.</p>
    );
  }
  return (
    <ol className="flex flex-col">
      {articles.map((article, i) => (
        <li key={article.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent" />
            {i < articles.length - 1 && (
              <span className="w-px flex-1 bg-border" />
            )}
          </div>
          <a
            href={article.url}
            target="_blank"
            rel="noreferrer"
            className="mb-3 flex flex-col gap-0.5 transition-colors
                       hover:text-accent"
          >
            <span className="text-sm text-ink">{article.title}</span>
            <span className="font-mono text-[10px] text-ink-mute">
              <span>{article.source}</span> ·{' '}
              {formatRelative(article.published_at)}
            </span>
          </a>
        </li>
      ))}
    </ol>
  );
}
