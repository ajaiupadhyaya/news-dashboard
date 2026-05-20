import type { Transition } from 'motion/react';

/** Spring presets — the dashboard's entire motion vocabulary. */
export const spring = {
  /** Calm; for layout shifts and large surfaces. */
  smooth: { type: 'spring', stiffness: 210, damping: 30, mass: 0.9 },
  /** Quick and tactile; for hover, press, and small controls. */
  snappy: { type: 'spring', stiffness: 440, damping: 34 },
  /** Soft landing; for elements entering the screen. */
  gentle: { type: 'spring', stiffness: 150, damping: 26 },
} satisfies Record<string, Transition>;

export const duration = { fast: 0.14, base: 0.26, slow: 0.5 } as const;

/** Easing for non-spring tweens (opacity, path morphs). */
export const easeOutExpo = [0.16, 1, 0.3, 1] as const;

/** Standard enter animation for cards and panels. */
export const fadeRise = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
} as const;
