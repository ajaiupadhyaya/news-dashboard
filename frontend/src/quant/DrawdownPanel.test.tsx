import { render, screen } from '@testing-library/react';
import { DrawdownPanel } from './DrawdownPanel';
import type { DrawdownPoint } from '../lib/quant-types';

function makeSeries(n: number): DrawdownPoint[] {
  return Array.from({ length: n }, (_, i) => ({
    date: new Date(Date.UTC(2024, 0, 1 + i)).toISOString().slice(0, 10),
    drawdown: -Math.abs(Math.sin(i / 10)) * 0.2,
  }));
}

test('renders the panel title', () => {
  render(<DrawdownPanel series={makeSeries(30)} />);
  expect(screen.getByText('Drawdown')).toBeInTheDocument();
});

test('renders an svg chart for a series with 30 points', () => {
  const { container } = render(<DrawdownPanel series={makeSeries(30)} />);
  expect(container.querySelector('svg')).not.toBeNull();
});

test('renders the chart container for a valid series', () => {
  const { container } = render(<DrawdownPanel series={makeSeries(30)} />);
  expect(container.querySelector('[data-testid="drawdown-chart"]')).not.toBeNull();
});

test('shows empty state when series is empty', () => {
  render(<DrawdownPanel series={[]} />);
  expect(screen.getByText('No drawdown data')).toBeInTheDocument();
});

test('shows empty state when series has only one point', () => {
  render(<DrawdownPanel series={makeSeries(1)} />);
  expect(screen.getByText('No drawdown data')).toBeInTheDocument();
});

test('renders area path and line path for valid series', () => {
  const { container } = render(<DrawdownPanel series={makeSeries(30)} />);
  const paths = container.querySelectorAll('path');
  // area fill + line stroke = at least 2 paths
  expect(paths.length).toBeGreaterThanOrEqual(2);
});
