import { screen, render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TradesTable } from './TradesTable';
import type { TradeRow } from '../lib/quant-types';

const trades: TradeRow[] = [
  {
    id: 1,
    strategy_slug: 'sma-crossover',
    date: '2026-01-10',
    symbol: 'AAPL',
    side: 'buy',
    qty: 100,
    price: 182.5,
    notional: 18250,
    phase: 'backtest',
  },
  {
    id: 2,
    strategy_slug: 'sma-crossover',
    date: '2026-03-15',
    symbol: 'NVDA',
    side: 'short',
    qty: 50,
    price: 850.0,
    notional: 42500,
    phase: 'forward',
  },
];

test('renders both trade rows', () => {
  render(<TradesTable trades={trades} />);
  expect(screen.getByText('AAPL')).toBeInTheDocument();
  expect(screen.getByText('NVDA')).toBeInTheDocument();
});

test('renders date values', () => {
  render(<TradesTable trades={trades} />);
  expect(screen.getByText('2026-01-10')).toBeInTheDocument();
  expect(screen.getByText('2026-03-15')).toBeInTheDocument();
});

test('renders side chips', () => {
  render(<TradesTable trades={trades} />);
  expect(screen.getByText('buy')).toBeInTheDocument();
  expect(screen.getByText('short')).toBeInTheDocument();
});

test('short side chip is italic red', () => {
  render(<TradesTable trades={trades} />);
  const shortChip = screen.getByText('short');
  expect(shortChip).toHaveStyle({ fontStyle: 'italic', color: '#f0506a' });
});

test('buy side chip is not italic', () => {
  render(<TradesTable trades={trades} />);
  const buyChip = screen.getByText('buy');
  expect(buyChip).toHaveStyle({ fontStyle: 'normal' });
});

test('renders phase labels', () => {
  render(<TradesTable trades={trades} />);
  expect(screen.getByText('backtest')).toBeInTheDocument();
  expect(screen.getByText('forward')).toBeInTheDocument();
});

test('renders notional values', () => {
  render(<TradesTable trades={trades} />);
  expect(screen.getByText('$18,250')).toBeInTheDocument();
  expect(screen.getByText('$42,500')).toBeInTheDocument();
});

test('renders empty state when trades is empty', () => {
  render(<TradesTable trades={[]} />);
  expect(screen.getByText('No trades yet')).toBeInTheDocument();
});

test('shows loading state', () => {
  render(<TradesTable trades={[]} isLoading={true} />);
  expect(screen.getByText('Loading…')).toBeInTheDocument();
});

test('shows Load more button when nextCursor is non-null', () => {
  const onLoadMore = vi.fn();
  render(<TradesTable trades={trades} nextCursor="cursor-abc" onLoadMore={onLoadMore} />);
  expect(screen.getByText('Load more')).toBeInTheDocument();
});

test('clicking Load more calls onLoadMore', async () => {
  const onLoadMore = vi.fn();
  const user = userEvent.setup();
  render(<TradesTable trades={trades} nextCursor="cursor-abc" onLoadMore={onLoadMore} />);
  await user.click(screen.getByText('Load more'));
  expect(onLoadMore).toHaveBeenCalledTimes(1);
});

test('does not show Load more button when nextCursor is null', () => {
  render(<TradesTable trades={trades} nextCursor={null} />);
  expect(screen.queryByText('Load more')).not.toBeInTheDocument();
});
