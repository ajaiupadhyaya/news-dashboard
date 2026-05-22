import { formatRelative, formatSourceCount, formatStatus } from './newsFormat';

const now = new Date('2026-05-22T12:00:00Z');

test('formatRelative renders minutes, hours, and days', () => {
  expect(formatRelative('2026-05-22T11:59:30Z', now)).toBe('just now');
  expect(formatRelative('2026-05-22T11:58:00Z', now)).toBe('2m ago');
  expect(formatRelative('2026-05-22T09:00:00Z', now)).toBe('3h ago');
  expect(formatRelative('2026-05-20T12:00:00Z', now)).toBe('2d ago');
});

test('formatSourceCount pluralizes', () => {
  expect(formatSourceCount(1)).toBe('1 source');
  expect(formatSourceCount(7)).toBe('7 sources');
});

test('formatStatus capitalizes the status', () => {
  expect(formatStatus('surging')).toBe('Surging');
  expect(formatStatus('steady')).toBe('Steady');
  expect(formatStatus('fading')).toBe('Fading');
});
