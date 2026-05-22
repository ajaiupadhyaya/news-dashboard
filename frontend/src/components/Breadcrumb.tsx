import { Fragment } from 'react';
import { Link } from 'react-router-dom';

export interface Crumb {
  label: string;
  /** Destination. Omit for the current (final) page. */
  to?: string;
}

/** The "← Dashboard / Finance / AAPL" trail. The first crumb carries a back
 *  arrow; the final crumb is rendered as plain text (the current page). */
export function Breadcrumb({ trail }: { trail: Crumb[] }) {
  return (
    <nav
      aria-label="Breadcrumb"
      className="flex flex-wrap items-center gap-1.5 font-mono text-xs
                 text-ink-mute"
    >
      {trail.map((crumb, i) => {
        const last = i === trail.length - 1;
        const text = i === 0 ? `← ${crumb.label}` : crumb.label;
        return (
          <Fragment key={crumb.label}>
            {i > 0 && <span aria-hidden="true">/</span>}
            {crumb.to ? (
              <Link
                to={crumb.to}
                viewTransition
                className="text-ink-soft transition-colors hover:text-accent"
              >
                {text}
              </Link>
            ) : (
              <span className={last ? 'text-ink' : undefined}>{text}</span>
            )}
          </Fragment>
        );
      })}
    </nav>
  );
}
