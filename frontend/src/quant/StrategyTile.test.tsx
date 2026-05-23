import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { StrategyTile } from './StrategyTile';
import type { StrategySummary } from '../lib/quant-types';

const summary: StrategySummary = {
  slug: 'sma-crossover',
  name: 'SMA Crossover',
  category: 'classic',
  sparkline: [1.0, 1.02, 1.05, 1.03, 1.08, 1.10, 1.07, 1.12],
  live_since: '2025-01-15',
  total_return: 0.2345,
  sharpe: 1.42,
  max_drawdown: -0.1234,
};

test('renders the strategy name', () => {
  renderWithProviders(<StrategyTile summary={summary} />);
  expect(screen.getByText('SMA Crossover')).toBeInTheDocument();
});

test('renders a sparkline svg', () => {
  const { container } = renderWithProviders(<StrategyTile summary={summary} />);
  expect(container.querySelector('svg')).not.toBeNull();
});

test('renders total return stat', () => {
  renderWithProviders(<StrategyTile summary={summary} />);
  expect(screen.getByText('+23.45%')).toBeInTheDocument();
});

test('renders sharpe stat', () => {
  renderWithProviders(<StrategyTile summary={summary} />);
  expect(screen.getByText('1.42')).toBeInTheDocument();
});

test('renders live-since chip', () => {
  renderWithProviders(<StrategyTile summary={summary} />);
  expect(screen.getByText('Live since 2025-01-15')).toBeInTheDocument();
});

test('renders "Backtest only" when live_since is null', () => {
  const backtestOnly: StrategySummary = { ...summary, live_since: null };
  renderWithProviders(<StrategyTile summary={backtestOnly} />);
  expect(screen.getByText('Backtest only')).toBeInTheDocument();
});

test('links to the strategy drill-down', () => {
  renderWithProviders(<StrategyTile summary={summary} />);
  expect(screen.getByRole('link')).toHaveAttribute('href', '/quant/strategy/sma-crossover');
});
