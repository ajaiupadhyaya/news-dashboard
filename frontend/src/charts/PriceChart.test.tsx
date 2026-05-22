import { render } from '@testing-library/react';
import { PriceChart } from './PriceChart';
import type { Bar, Technicals } from '../lib/types';

function makeBars(n: number): Bar[] {
  return Array.from({ length: n }, (_, i) => ({
    date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
    open: 100 + i, high: 106 + i, low: 95 + i, close: 102 + i, volume: 1000,
  }));
}

const emptyTechnicals: Technicals = {
  sma_20: [], sma_50: [], sma_200: [],
};

test('candle mode renders one body rect per bar', () => {
  const bars = makeBars(20);
  const { container } = render(
    <PriceChart bars={bars} technicals={emptyTechnicals}
      chartType="candle" showSma={false} showBollinger={false} />,
  );
  // 20 candle bodies + 1 transparent pointer-capture overlay
  expect(container.querySelectorAll('rect').length).toBe(21);
});

test('line mode renders a price path, no candle bodies', () => {
  const bars = makeBars(20);
  const { container } = render(
    <PriceChart bars={bars} technicals={emptyTechnicals}
      chartType="line" showSma={false} showBollinger={false} />,
  );
  expect(container.querySelectorAll('path').length).toBeGreaterThan(0);
  // only the pointer-capture overlay rect
  expect(container.querySelectorAll('rect').length).toBe(1);
});

test('renders nothing for empty bars', () => {
  const { container } = render(
    <PriceChart bars={[]} technicals={emptyTechnicals}
      chartType="candle" showSma={false} showBollinger={false} />,
  );
  expect(container.querySelector('svg')).toBeNull();
});
