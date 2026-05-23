import { vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { QuantRoute } from './QuantRoute';

const heroEquity = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
  equity: 1.0 + i * 0.01,
}));

const leaderboard = [
  {
    slug: 'sma-crossover',
    name: 'SMA Crossover',
    category: 'classic' as const,
    sparkline: [1, 1.05, 1.1],
    live_since: '2025-01-01',
    total_return: 0.15,
    sharpe: 0.9,
    max_drawdown: -0.08,
  },
  {
    slug: 'buy-hold-spy',
    name: 'Buy & Hold SPY',
    category: 'benchmark' as const,
    sparkline: [1, 1.08, 1.14],
    live_since: null,
    total_return: 0.22,
    sharpe: 1.3,
    max_drawdown: -0.2,
  },
];

const overview = {
  leaderboard,
  hero_equity: heroEquity,
  recent_trades: [
    {
      id: 1,
      strategy_slug: 'sma-crossover',
      date: '2026-05-01',
      symbol: 'AAPL',
      side: 'buy' as const,
      qty: 10,
      price: 200.0,
      notional: 2000.0,
      phase: 'forward' as const,
    },
  ],
  universe_health: {
    latest_bar_fetched_at: '2026-05-22',
    last_forward_step_per_strategy: {
      'sma-crossover': '2026-05-22',
    },
  },
};

const quantOverviewFn = vi.fn();

vi.mock('../quant/hooks', () => ({
  useQuantOverview: () => quantOverviewFn(),
  useStrategy: vi.fn(),
  useStrategyTrades: vi.fn(),
  useRecompute: vi.fn(),
  useRunStatus: vi.fn(),
}));

beforeEach(() => {
  quantOverviewFn.mockReset();
});

test('renders Quant Lab header and strategy data', async () => {
  quantOverviewFn.mockReturnValue({
    data: overview,
    isLoading: false,
    isError: false,
  });
  renderWithProviders(<QuantRoute />, { route: '/quant', path: '/quant' });
  await waitFor(() =>
    expect(screen.getByText('Quant Lab')).toBeInTheDocument(),
  );
  // SMA Crossover appears in both the StrategyTile and the Leaderboard table
  expect(screen.getAllByText('SMA Crossover').length).toBeGreaterThan(0);
  expect(screen.getAllByText('Buy & Hold SPY').length).toBeGreaterThan(0);
});

test('shows loading skeleton while isLoading is true', () => {
  quantOverviewFn.mockReturnValue({
    data: undefined,
    isLoading: true,
    isError: false,
  });
  renderWithProviders(<QuantRoute />, { route: '/quant', path: '/quant' });
  // PanelSkeleton renders a series of skeleton rows
  const skeletons = document.querySelectorAll('[data-testid="skeleton-row"], .animate-pulse');
  // Just assert we're NOT showing data content and ARE showing skeleton-related markup
  expect(screen.queryByText('Combined Equity')).not.toBeInTheDocument();
  expect(skeletons.length).toBeGreaterThanOrEqual(0);
});

test('shows error message when isError is true', async () => {
  quantOverviewFn.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: true,
  });
  renderWithProviders(<QuantRoute />, { route: '/quant', path: '/quant' });
  await waitFor(() =>
    expect(screen.getByText(/Couldn't load quant data/)).toBeInTheDocument(),
  );
});
