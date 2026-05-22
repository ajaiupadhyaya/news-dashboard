import { render } from '@testing-library/react';
import { VolumeChart } from './VolumeChart';
import type { Bar } from '../lib/types';

function makeBars(n: number): Bar[] {
  return Array.from({ length: n }, (_, i) => ({
    date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
    open: 100, high: 101, low: 99, close: i % 2 ? 100.5 : 99.5,
    volume: 1000 + i * 10,
  }));
}

test('renders one volume bar per input bar', () => {
  const { container } = render(<VolumeChart bars={makeBars(15)} />);
  expect(container.querySelectorAll('rect').length).toBe(15);
});

test('renders nothing for empty bars', () => {
  const { container } = render(<VolumeChart bars={[]} />);
  expect(container.querySelector('svg')).toBeNull();
});
