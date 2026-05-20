import type { ReactNode } from 'react';
import { motion } from 'motion/react';
import { clsx } from 'clsx';
import { fadeRise, spring } from '../design/motion';

interface PanelProps {
  title: string;
  icon: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** The shared frame for every domain panel — header bar plus body. */
export function Panel({ title, icon, action, children, className }: PanelProps) {
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
          <h2 className="font-mono text-xs tracking-widest text-ink-soft uppercase">
            {title}
          </h2>
        </div>
        {action}
      </header>
      <div className="flex-1 p-4">{children}</div>
    </motion.section>
  );
}
