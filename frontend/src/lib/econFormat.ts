import { formatCompact } from './format';

/**
 * Format an economic indicator's headline value for display, by its unit.
 * "%" -> "4.1%"; "K" -> a compact person count; "index"/other -> 1-decimal.
 */
export function formatIndicatorValue(value: number, unit: string): string {
  switch (unit) {
    case '%':
      return `${value.toFixed(1)}%`;
    case 'K': // FRED level in thousands -> compact ("159M", "150k")
      return formatCompact(value * 1000);
    case '$':
      return formatCompact(value);
    default: // "index" and anything else
      return value.toFixed(1);
  }
}

/** Format an indicator's change vs. the prior release, signed, by its unit. */
export function formatIndicatorChange(change: number, unit: string): string {
  if (unit === 'K') {
    const mag = formatCompact(Math.abs(change) * 1000);
    return change < 0 ? `-${mag}` : `+${mag}`;
  }
  const sign = change > 0 ? '+' : '';
  if (unit === '%') return `${sign}${change.toFixed(1)}pp`;
  return `${sign}${change.toFixed(1)}`;
}
