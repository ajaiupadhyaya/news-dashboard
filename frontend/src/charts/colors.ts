import { scaleLinear } from 'd3-scale';
import { tokens } from '../design/tokens';

const heat = scaleLinear<string>()
  .domain([-2, 0, 2])
  .range([tokens.color.down, tokens.color.raised, tokens.color.up])
  .clamp(true);

/** Diverging heat color for a percent change (down ↔ flat ↔ up). */
export function heatColor(changePct: number): string {
  if (changePct >= 2) return tokens.color.up;
  if (changePct <= -2) return tokens.color.down;
  return heat(changePct);
}

/** Semantic color for a signed value. */
export function trendColor(n: number): string {
  if (n > 0) return tokens.color.up;
  if (n < 0) return tokens.color.down;
  return tokens.color.flat;
}

/** Stroke colors for the moving-average overlays on the candlestick chart. */
export const smaColor = {
  20: tokens.color.accent,
  50: '#d2a44e',
  200: tokens.color.inkSoft,
} as const;
