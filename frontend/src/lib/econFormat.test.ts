import { formatIndicatorChange, formatIndicatorValue } from './econFormat';

test('formats percent values', () => {
  expect(formatIndicatorValue(4.12, '%')).toBe('4.1%');
});

test('formats index values', () => {
  expect(formatIndicatorValue(310.27, 'index')).toBe('310.3');
});

test('formats large "K" (thousands) levels compactly', () => {
  // PAYEMS is reported in thousands of persons.
  expect(formatIndicatorValue(159000, 'K')).toBe('159M');
});

test('formats a signed percent-point change', () => {
  expect(formatIndicatorChange(-0.1, '%')).toBe('-0.1pp');
  expect(formatIndicatorChange(0.3, '%')).toBe('+0.3pp');
});

test('formats a signed "K" change compactly', () => {
  expect(formatIndicatorChange(150, 'K')).toBe('+150k');
  expect(formatIndicatorChange(-80, 'K')).toBe('-80k');
});
