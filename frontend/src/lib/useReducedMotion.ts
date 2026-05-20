import { useReducedMotion as useMotionReducedMotion } from 'motion/react';

/** True when the user has requested reduced motion. */
export function useReducedMotion(): boolean {
  return useMotionReducedMotion() ?? false;
}

/**
 * Duration (ms) for D3-driven chart animations — `MotionConfig` does not
 * cover D3 transitions, so chart code reads this directly. 0 when reduced
 * motion is on.
 */
export function useChartAnimationMs(base = 450): number {
  return useReducedMotion() ? 0 : base;
}
