import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import { clsx } from 'clsx';
import { fadeRise, spring } from '../design/motion';

interface PanelProps {
  title: string;
  icon: string;
  /** When set, the panel title becomes a link to this domain page. */
  href?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** The shared frame for every domain panel — header bar plus body. When
 *  `href` is set the title links to the domain page. */
export function Panel({
  title, icon, href, action, children, className,
}: PanelProps) {
  const heading = (
    <h2
      className={clsx(
        'font-mono text-xs tracking-widest uppercase transition-colors',
        href ? 'text-ink-soft hover:text-accent' : 'text-ink-soft',
      )}
    >
      {title}
    </h2>
  );

  return (
    <motion.section
      initial={fadeRise.initial}
      animate={fadeRise.animate}
      transition={spring.gentle}
      className={clsx(
        'flex flex-col overflow-hidden rounded-lg border border-border bg-surface',
        className,
      )}
    >
      <header className="flex items-center justify-between border-b border-border
                         px-4 py-3">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="text-base">{icon}</span>
          {href ? (
            <Link to={href} viewTransition aria-label={`Open ${title}`}>
              {heading}
            </Link>
          ) : (
            heading
          )}
        </div>
        {action}
      </header>
      <div className="flex-1 p-4">{children}</div>
    </motion.section>
  );
}
