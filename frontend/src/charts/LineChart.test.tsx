import { render } from '@testing-library/react';
import { LineChart } from './LineChart';
import type { IndicatorPoint } from '../lib/types';

function makePoints(n: number): IndicatorPoint[] {
  return Array.from({ length: n }, (_, i) => ({
    date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
    value: 100 + Math.sin(i / 5) * 10,
  }));
}

test('renders an area path and a line path for the series', () => {
  const { container } = render(<LineChart points={makePoints(40)} />);
  expect(container.querySelector('svg')).not.toBeNull();
  // exactly two <path>: the area fill and the line stroke
  expect(container.querySelectorAll('path')).toHaveLength(2);
});

test('renders nothing for a series shorter than two points', () => {
  const { container } = render(<LineChart points={makePoints(1)} />);
  expect(container.querySelector('svg')).toBeNull();
});
