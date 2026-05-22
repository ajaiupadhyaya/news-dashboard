import type { ReactNode } from 'react';
import { motion } from 'motion/react';
import { clsx } from 'clsx';
import { fadeRise, spring } from '../design/motion';

/** The bento layout: a 6-column grid on large screens, one column below. */
export function BentoGrid({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-6">{children}</div>
  );
}

// Literal class strings so Tailwind's source scan picks every span up.
const COL_SPAN: Record<number, string> = {
  1: 'lg:col-span-1',
  2: 'lg:col-span-2',
  3: 'lg:col-span-3',
  4: 'lg:col-span-4',
  5: 'lg:col-span-5',
  6: 'lg:col-span-6',
};

interface BentoTileProps {
  /** Optional uppercase section header. Omit when the child renders its own. */
  title?: string;
  /** Columns to span on large screens (1-6). Full width below `lg`. */
  colSpan?: 1 | 2 | 3 | 4 | 5 | 6;
  children: ReactNode;
  className?: string;
}

/** One tile in the bento grid — a bordered surface card that enters with a
 *  soft rise, with an optional uppercase section header. */
export function BentoTile({
  title, colSpan = 2, children, className,
}: BentoTileProps) {
  return (
    <motion.section
      initial={fadeRise.initial}
      animate={fadeRise.animate}
      transition={spring.gentle}
      className={clsx(
        'flex flex-col overflow-hidden rounded-lg border border-border',
        'bg-surface p-4',
        COL_SPAN[colSpan],
        className,
      )}
    >
      {title && (
        <h2 className="mb-3 font-mono text-[10px] tracking-widest text-ink-mute
                       uppercase">
          {title}
        </h2>
      )}
      <div className="flex-1">{children}</div>
    </motion.section>
  );
}
