import { screen, render } from '@testing-library/react';
import { RecentTradesPanel } from './RecentTradesPanel';
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
    strategy_slug: 'news-momentum',
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
  render(<RecentTradesPanel trades={trades} />);
  expect(screen.getByText('AAPL')).toBeInTheDocument();
  expect(screen.getByText('NVDA')).toBeInTheDocument();
});

test('renders correct date values', () => {
  render(<RecentTradesPanel trades={trades} />);
  expect(screen.getByText('2026-01-10')).toBeInTheDocument();
  expect(screen.getByText('2026-03-15')).toBeInTheDocument();
});

test('renders side chip with correct text', () => {
  render(<RecentTradesPanel trades={trades} />);
  expect(screen.getByText('buy')).toBeInTheDocument();
  expect(screen.getByText('short')).toBeInTheDocument();
});

test('renders phase chip with correct text', () => {
  render(<RecentTradesPanel trades={trades} />);
  expect(screen.getByText('backtest')).toBeInTheDocument();
  expect(screen.getByText('forward')).toBeInTheDocument();
});

test('renders notional values', () => {
  render(<RecentTradesPanel trades={trades} />);
  expect(screen.getByText('$18,250')).toBeInTheDocument();
  expect(screen.getByText('$42,500')).toBeInTheDocument();
});

test('renders strategy slugs', () => {
  render(<RecentTradesPanel trades={trades} />);
  expect(screen.getByText('sma-crossover')).toBeInTheDocument();
  expect(screen.getByText('news-momentum')).toBeInTheDocument();
});

test('renders empty state when trades array is empty', () => {
  render(<RecentTradesPanel trades={[]} />);
  expect(screen.getByText('No trades yet.')).toBeInTheDocument();
});
