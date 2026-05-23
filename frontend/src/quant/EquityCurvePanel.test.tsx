import { render, screen } from '@testing-library/react';
import { EquityCurvePanel } from './EquityCurvePanel';
import type { EquityPoint } from '../lib/quant-types';

function makeBacktestSeries(n: number): EquityPoint[] {
  return Array.from({ length: n }, (_, i) => ({
    date: new Date(Date.UTC(2024, 0, 1 + i)).toISOString().slice(0, 10),
    equity: 1.0 + i * 0.005,
    phase: 'backtest' as const,
    daily_return: 0.005,
  }));
}

function makeForwardSeries(n: number, startYear = 2025): EquityPoint[] {
  return Array.from({ length: n }, (_, i) => ({
    date: new Date(Date.UTC(startYear, 0, 1 + i)).toISOString().slice(0, 10),
    equity: 1.5 + i * 0.008,
    phase: 'forward' as const,
    daily_return: 0.008,
  }));
}

test('renders the panel title', () => {
  render(<EquityCurvePanel series={makeBacktestSeries(30)} />);
  expect(screen.getByText('Equity Curve')).toBeInTheDocument();
});

test('renders an svg for a backtest-only series', () => {
  const { container } = render(<EquityCurvePanel series={makeBacktestSeries(30)} />);
  expect(container.querySelector('svg')).not.toBeNull();
});

test('renders both backtest and forward chart containers for mixed series', () => {
  const mixed = [...makeBacktestSeries(30), ...makeForwardSeries(20)];
  const { container } = render(<EquityCurvePanel series={mixed} />);
  expect(container.querySelector('[data-testid="equity-backtest-chart"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="equity-forward-chart"]')).not.toBeNull();
});

test('renders a "Live" legend item when forward data is present', () => {
  const mixed = [...makeBacktestSeries(30), ...makeForwardSeries(20)];
  render(<EquityCurvePanel series={mixed} />);
  expect(screen.getByText('Live')).toBeInTheDocument();
  expect(screen.getByText('Backtest')).toBeInTheDocument();
});

test('shows empty state message for series with less than 2 points', () => {
  render(<EquityCurvePanel series={[]} />);
  expect(screen.getByText('No equity data')).toBeInTheDocument();
});

test('renders only backtest chart when no forward data', () => {
  const { container } = render(<EquityCurvePanel series={makeBacktestSeries(30)} />);
  expect(container.querySelector('[data-testid="equity-backtest-chart"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="equity-forward-chart"]')).toBeNull();
});
