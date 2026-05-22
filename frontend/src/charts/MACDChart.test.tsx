import { render } from '@testing-library/react';
import { MACDChart } from './MACDChart';

function ramp(n: number, fromNull: number): (number | null)[] {
  return Array.from({ length: n }, (_, i) =>
    i < fromNull ? null : Math.sin(i / 4),
  );
}

test('renders MACD and signal paths plus histogram bars', () => {
  const macdLine = ramp(40, 25);
  const signal = ramp(40, 25);
  const histogram = ramp(40, 25);
  const { container } = render(
    <MACDChart line={macdLine} signal={signal} histogram={histogram} />,
  );
  expect(container.querySelectorAll('path').length).toBe(2); // macd + signal
  expect(container.querySelectorAll('rect').length).toBe(15); // 40 - 25
});

test('renders nothing without enough data', () => {
  const { container } = render(
    <MACDChart line={[null]} signal={[null]} histogram={[null]} />,
  );
  expect(container.querySelector('svg')).toBeNull();
});
