import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { LeaderboardPanel } from './LeaderboardPanel';
import type { StrategySummary } from '../lib/quant-types';

const entries: StrategySummary[] = [
  {
    slug: 'sma-crossover',
    name: 'SMA Crossover',
    category: 'classic',
    sparkline: [1, 1.05, 1.1],
    live_since: '2025-01-01',
    total_return: 0.15,
    sharpe: 0.9,
    max_drawdown: -0.08,
  },
  {
    slug: 'news-momentum',
    name: 'News Momentum',
    category: 'alpha',
    sparkline: [1, 1.1, 1.25],
    live_since: '2025-03-01',
    total_return: 0.42,
    sharpe: 2.1,
    max_drawdown: -0.12,
  },
  {
    slug: 'buy-hold-spy',
    name: 'Buy & Hold SPY',
    category: 'benchmark',
    sparkline: [1, 1.08, 1.14],
    live_since: null,
    total_return: 0.22,
    sharpe: 1.3,
    max_drawdown: -0.2,
  },
];

test('renders all strategy names', () => {
  renderWithProviders(<LeaderboardPanel entries={entries} />);
  expect(screen.getByText('SMA Crossover')).toBeInTheDocument();
  expect(screen.getByText('News Momentum')).toBeInTheDocument();
  expect(screen.getByText('Buy & Hold SPY')).toBeInTheDocument();
});

test('default sort is sharpe desc — News Momentum (2.1) first', () => {
  renderWithProviders(<LeaderboardPanel entries={entries} />);
  const rows = screen.getAllByRole('row');
  // rows[0] is header, rows[1] is first data row
  expect(rows[1]).toHaveTextContent('News Momentum');
});

test('clicking Total Return header changes sort order', () => {
  renderWithProviders(<LeaderboardPanel entries={entries} />);
  const totalReturnHeader = screen.getByText(/Total Return/i);
  fireEvent.click(totalReturnHeader);
  // After clicking Total Return (default dir = desc), News Momentum (0.42) should be first
  const rows = screen.getAllByRole('row');
  expect(rows[1]).toHaveTextContent('News Momentum');
});

test('clicking same header toggles direction', () => {
  renderWithProviders(<LeaderboardPanel entries={entries} />);
  const sharpeHeader = screen.getByText(/Sharpe/);
  // Click once -> now asc
  fireEvent.click(sharpeHeader);
  const rows = screen.getAllByRole('row');
  // Asc sharpe: SMA Crossover (0.9) should be first
  expect(rows[1]).toHaveTextContent('SMA Crossover');
});

test('strategy names link to strategy drill-down', () => {
  renderWithProviders(<LeaderboardPanel entries={entries} />);
  const link = screen.getByRole('link', { name: 'News Momentum' });
  expect(link).toHaveAttribute('href', '/quant/strategy/news-momentum');
});

test('shows dash for null live_since', () => {
  renderWithProviders(<LeaderboardPanel entries={entries} />);
  // "—" appears for Buy & Hold SPY which has live_since: null
  expect(screen.getAllByText('—').length).toBeGreaterThan(0);
});
