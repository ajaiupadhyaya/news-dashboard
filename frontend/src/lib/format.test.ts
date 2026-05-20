import {
  trendOf, formatPrice, formatPercent, formatChange,
  formatCompact, formatDay, formatFullDate, formatUpdated,
} from './format';

test('trendOf classifies signed numbers', () => {
  expect(trendOf(1.2)).toBe('up');
  expect(trendOf(-0.3)).toBe('down');
  expect(trendOf(0)).toBe('flat');
});

test('formatPrice renders USD with two decimals', () => {
  expect(formatPrice(1234.5)).toBe('$1,234.50');
  expect(formatPrice(9.1)).toBe('$9.10');
});

test('formatPercent signs positives and formats to two decimals', () => {
  expect(formatPercent(1.234)).toBe('+1.23%');
  expect(formatPercent(-0.5)).toBe('-0.50%');
  expect(formatPercent(2.5, { sign: false })).toBe('2.50%');
});

test('formatChange signs the raw number', () => {
  expect(formatChange(1.8)).toBe('+1.80');
  expect(formatChange(-2)).toBe('-2.00');
});

test('formatCompact abbreviates large numbers and uses B for billions', () => {
  expect(formatCompact(3.42e12)).toBe('3.42T');
  expect(formatCompact(3.24e11)).toBe('324B');
  expect(formatCompact(null)).toBe('—');
});

test('formatDay and formatFullDate render UTC dates without TZ drift', () => {
  expect(formatDay('2026-05-20')).toBe('May 20');
  expect(formatFullDate('2026-05-20')).toBe('May 20, 2026');
});

test('formatUpdated produces an "Updated <time>" label', () => {
  expect(formatUpdated('2026-05-20T20:00:00+00:00')).toMatch(
    /^Updated \d{1,2}:\d{2} (AM|PM)$/,
  );
});
