import { screen, render } from '@testing-library/react';
import { MethodologyPanel } from './MethodologyPanel';
import type { StrategyDetail } from '../lib/quant-types';

const detail: StrategyDetail = {
  slug: 'sma-crossover',
  name: 'SMA Crossover',
  category: 'classic',
  methodology_blurb:
    'A dual moving-average strategy that goes long when the fast SMA crosses above the slow SMA.',
  universe_kind: 'sp500',
  inception_date: '2020-01-02',
  live_start_date: '2025-01-15',
  chosen_params: { fast_window: 20, slow_window: 50 },
  cost_model: { commission: 1.0, slippage_bps: 5, allow_short: true },
  last_forward_step_date: '2026-05-20',
  equity_series: [],
  drawdown_series: [],
  monthly_returns: {},
  tear_sheet: { total_return: 0.45, sharpe: 1.42, max_drawdown: -0.12 },
  walkforward_windows: [],
  param_sweep: [],
  current_positions: [],
  recent_trades: [],
};

test('renders Methodology heading', () => {
  render(<MethodologyPanel detail={detail} />);
  expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Methodology');
});

test('renders methodology blurb text', () => {
  render(<MethodologyPanel detail={detail} />);
  expect(screen.getByText(/dual moving-average strategy/)).toBeInTheDocument();
});

test('renders chosen param chips', () => {
  render(<MethodologyPanel detail={detail} />);
  expect(screen.getByTestId('param-chip-fast_window')).toHaveTextContent('fast_window=20');
  expect(screen.getByTestId('param-chip-slow_window')).toHaveTextContent('slow_window=50');
});

test('renders cost model line with commission and slippage', () => {
  render(<MethodologyPanel detail={detail} />);
  const costLine = screen.getByTestId('cost-model-line');
  expect(costLine).toHaveTextContent('Commission: $1.00');
  expect(costLine).toHaveTextContent('Slippage: 5 bps');
  expect(costLine).toHaveTextContent('Short: enabled');
});

test('renders cost model with short disabled', () => {
  const noShort: StrategyDetail = {
    ...detail,
    cost_model: { ...detail.cost_model, allow_short: false },
  };
  render(<MethodologyPanel detail={noShort} />);
  expect(screen.getByTestId('cost-model-line')).toHaveTextContent('Short: disabled');
});

test('renders live since and inception dates in footer', () => {
  render(<MethodologyPanel detail={detail} />);
  expect(screen.getByText(/Live since 2025-01-15/)).toBeInTheDocument();
  expect(screen.getByText(/Inception 2020-01-02/)).toBeInTheDocument();
});
