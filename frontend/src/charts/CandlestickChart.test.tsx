import { render } from '@testing-library/react';
import { CandlestickChart } from './CandlestickChart';
import type { Bar, Technicals } from '../lib/types';

function makeBars(n: number): Bar[] {
  return Array.from({ length: n }, (_, i) => {
    const date = new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10);
    return {
      date,
      open: 100 + i,
      high: 106 + i,
      low: 95 + i,
      close: 102 + i,
      volume: 1000,
    };
  });
}

test('renders one candle body per bar plus three SMA overlays', () => {
  const bars = makeBars(30);
  const technicals: Technicals = {
    sma_20: bars.map((b) => b.close),
    sma_50: bars.map(() => null),
    sma_200: bars.map(() => null),
  };
  const { container } = render(
    <CandlestickChart bars={bars} technicals={technicals} />,
  );
  expect(container.querySelectorAll('path')).toHaveLength(3);
  // one rect per candle body + the transparent pointer-capture overlay
  expect(container.querySelectorAll('rect')).toHaveLength(bars.length + 1);
});

test('renders nothing for an empty bar list without crashing', () => {
  const empty: Technicals = { sma_20: [], sma_50: [], sma_200: [] };
  const { container } = render(
    <CandlestickChart bars={[]} technicals={empty} />,
  );
  expect(container.querySelector('svg')).toBeNull();
});
