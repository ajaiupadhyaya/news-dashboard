import { heatColor, trendColor, smaColor } from './colors';
import { tokens } from '../design/tokens';

test('heatColor maps strong gains to the up color and losses to down', () => {
  expect(heatColor(2)).toBe(tokens.color.up);
  expect(heatColor(-2)).toBe(tokens.color.down);
});

test('trendColor returns semantic colors for signed values', () => {
  expect(trendColor(1)).toBe(tokens.color.up);
  expect(trendColor(-1)).toBe(tokens.color.down);
  expect(trendColor(0)).toBe(tokens.color.flat);
});

test('smaColor has a distinct color per moving-average window', () => {
  expect(new Set([smaColor[20], smaColor[50], smaColor[200]]).size).toBe(3);
});
