import { format } from 'd3-format';
import { utcFormat, timeFormat } from 'd3-time-format';

const compact = format('.3~s');
const utcDay = utcFormat('%b %-d');
const utcDayYear = utcFormat('%b %-d, %Y');
const localTime = timeFormat('%-I:%M %p');

export type Trend = 'up' | 'down' | 'flat';

/** Classify a signed number into a market trend direction. */
export function trendOf(n: number): Trend {
  if (n > 0) return 'up';
  if (n < 0) return 'down';
  return 'flat';
}

/** "$1,234.50" — USD, always two decimals. */
export function formatPrice(n: number): string {
  return n.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** "+1.23%" / "-0.50%". Input is already a percent number. */
export function formatPercent(n: number, opts: { sign?: boolean } = {}): string {
  const sign = opts.sign !== false && n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

/** "+1.80" / "-2.00" — signed plain number, two decimals. */
export function formatChange(n: number): string {
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}`;
}

/** Large numbers as "3.42T", "324B", "12.0M"; "—" for null/non-finite. */
export function formatCompact(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return '—';
  return compact(n).replace('G', 'B');
}

/** "May 20" — formats a date-only or ISO string in UTC (no TZ drift). */
export function formatDay(iso: string): string {
  return utcDay(new Date(iso));
}

/** "May 20, 2026" — formats a date-only or ISO string in UTC. */
export function formatFullDate(iso: string): string {
  return utcDayYear(new Date(iso));
}

/** "Updated 3:45 PM" — local time, for `updated_at` datetimes. */
export function formatUpdated(iso: string): string {
  return `Updated ${localTime(new Date(iso))}`;
}

/** "5,400.00" — a plain number with thousands separators and two decimals.
 *  For index levels, yields, and other non-currency values where the "$" of
 *  `formatPrice` would be wrong. */
export function formatValue(n: number): string {
  return n.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
