import { motion } from 'motion/react';
import { spring } from '../design/motion';

/** Full-width strip below the app bar. Placeholder until the Phase 5 AI layer. */
export function BriefingRibbon() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={spring.smooth}
      className="border-b border-border bg-surface px-5 py-3"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-mono text-[10px] tracking-widest text-accent uppercase">
          Daily Briefing
        </span>
        <p className="text-sm text-ink-soft">
          AI synthesis of the day's news, markets, and politics arrives in a
          later phase.
        </p>
      </div>
    </motion.div>
  );
}
