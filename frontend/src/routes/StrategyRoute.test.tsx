import { vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { StrategyRoute } from './StrategyRoute';
import { ApiError } from '../lib/api';

const equitySeries = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
  equity: 1.0 + i * 0.01,
  phase: i < 20 ? ('backtest' as const) : ('forward' as const),
  daily_return: 0.001,
}));

const drawdownSeries = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
  drawdown: -Math.abs(Math.sin(i / 5) * 0.05),
}));

const strategyDetail = {
  slug: 'buy-hold-spy',
  name: 'Buy & Hold SPY',
  category: 'benchmark',
  methodology_blurb:
    'Simply holds SPY for the full duration, providing a passive benchmark.',
  universe_kind: 'index',
  inception_date: '2020-01-01',
  live_start_date: '2025-01-01',
  chosen_params: { rebalance: 'monthly' },
  cost_model: { commission: 0.0, slippage_bps: 0, allow_short: false },
  last_forward_step_date: '2026-05-22',
  equity_series: equitySeries,
  drawdown_series: drawdownSeries,
  monthly_returns: {
    '2026': { 1: 0.03, 2: -0.01, 3: 0.04 },
  },
  tear_sheet: { total_return: 0.32, sharpe: 1.4, max_drawdown: -0.18 },
  walkforward_windows: [],
  param_sweep: [],
  current_positions: [
    { symbol: 'SPY', qty: 100, avg_cost: 470.0, opened_at: '2026-01-02' },
  ],
  recent_trades: [],
};

const strategyFn = vi.fn();
const tradesFn = vi.fn();

vi.mock('../quant/hooks', () => ({
  useStrategy: (slug: string) => strategyFn(slug),
  useStrategyTrades: (slug: string) => tradesFn(slug),
  useQuantOverview: vi.fn(),
  useRecompute: () => ({
    mutate: vi.fn(),
    isPending: false,
    data: undefined,
    isError: false,
  }),
  useRunStatus: () => ({
    data: undefined,
    isLoading: false,
  }),
}));

beforeEach(() => {
  strategyFn.mockReset();
  tradesFn.mockReset();
  tradesFn.mockReturnValue({
    data: { trades: [], next_cursor: null },
    isLoading: false,
    isError: false,
  });
});

test('renders the strategy name and methodology', async () => {
  strategyFn.mockReturnValue({
    data: strategyDetail,
    isLoading: false,
    isError: false,
    error: undefined,
  });
  renderWithProviders(<StrategyRoute />, {
    route: '/quant/strategy/buy-hold-spy',
    path: '/quant/strategy/:slug',
  });
  await waitFor(() =>
    expect(
      screen.getByRole('heading', { name: 'Buy & Hold SPY' }),
    ).toBeInTheDocument(),
  );
  // Methodology blurb appears inside the MethodologyPanel
  expect(
    screen.getByText(/Simply holds SPY for the full duration/),
  ).toBeInTheDocument();
  // Breadcrumb shows the strategy name
  expect(screen.getAllByText('Buy & Hold SPY').length).toBeGreaterThan(0);
});

test('shows strategy headline metrics', async () => {
  strategyFn.mockReturnValue({
    data: strategyDetail,
    isLoading: false,
    isError: false,
    error: undefined,
  });
  renderWithProviders(<StrategyRoute />, {
    route: '/quant/strategy/buy-hold-spy',
    path: '/quant/strategy/:slug',
  });
  await waitFor(() =>
    expect(screen.getByText('Total Return')).toBeInTheDocument(),
  );
  expect(screen.getByText('Sharpe')).toBeInTheDocument();
  expect(screen.getByText('Max Drawdown')).toBeInTheDocument();
  expect(screen.getByText('Live Since')).toBeInTheDocument();
});

test('shows loading skeleton while isLoading is true', () => {
  strategyFn.mockReturnValue({
    data: undefined,
    isLoading: true,
    isError: false,
    error: undefined,
  });
  renderWithProviders(<StrategyRoute />, {
    route: '/quant/strategy/buy-hold-spy',
    path: '/quant/strategy/:slug',
  });
  expect(screen.queryByRole('heading', { name: 'Buy & Hold SPY' })).not.toBeInTheDocument();
});

test('shows 404 message when strategy is not found', async () => {
  strategyFn.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: true,
    error: new ApiError(404, 'Strategy not found'),
  });
  renderWithProviders(<StrategyRoute />, {
    route: '/quant/strategy/nonexistent',
    path: '/quant/strategy/:slug',
  });
  await waitFor(() =>
    expect(screen.getByText(/Strategy not found/)).toBeInTheDocument(),
  );
});
