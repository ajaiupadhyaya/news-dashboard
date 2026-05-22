import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { TimeframeControl, ChartTypeToggle } from './ChartControls';

test('TimeframeControl renders all timeframes and marks the active one', () => {
  render(<TimeframeControl value="1y" onChange={() => {}} />);
  expect(screen.getByRole('button', { name: '1M' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'MAX' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '1Y' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
});

test('TimeframeControl reports the chosen timeframe', () => {
  const onChange = vi.fn();
  render(<TimeframeControl value="1y" onChange={onChange} />);
  fireEvent.click(screen.getByRole('button', { name: '5Y' }));
  expect(onChange).toHaveBeenCalledWith('5y');
});

test('ChartTypeToggle reports the chosen type', () => {
  const onChange = vi.fn();
  render(<ChartTypeToggle value="candle" onChange={onChange} />);
  fireEvent.click(screen.getByRole('button', { name: 'Line' }));
  expect(onChange).toHaveBeenCalledWith('line');
});
