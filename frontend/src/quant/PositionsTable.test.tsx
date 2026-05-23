import { screen, render } from '@testing-library/react';
import { PositionsTable } from './PositionsTable';
import type { PositionRow } from '../lib/quant-types';

const positions: PositionRow[] = [
  {
    symbol: 'AAPL',
    qty: 100,
    avg_cost: 182.5,
    opened_at: '2026-01-10',
  },
  {
    symbol: 'NVDA',
    qty: -50,
    avg_cost: 850.0,
    opened_at: '2026-03-15',
  },
];

test('renders both position rows', () => {
  render(<PositionsTable positions={positions} />);
  expect(screen.getByText('AAPL')).toBeInTheDocument();
  expect(screen.getByText('NVDA')).toBeInTheDocument();
});

test('renders long qty with positive sign', () => {
  render(<PositionsTable positions={positions} />);
  expect(screen.getByText('+100')).toBeInTheDocument();
});

test('renders short qty with negative value in italic red', () => {
  render(<PositionsTable positions={positions} />);
  const shortCell = screen.getByTestId('qty-short');
  expect(shortCell).toBeInTheDocument();
  expect(shortCell).toHaveStyle({ fontStyle: 'italic', color: '#f0506a' });
  expect(shortCell.textContent).toBe('-50');
});

test('renders long qty without italic styling', () => {
  render(<PositionsTable positions={positions} />);
  const longCell = screen.getByTestId('qty-long');
  expect(longCell).toHaveStyle({ fontStyle: 'normal' });
});

test('renders avg cost values', () => {
  render(<PositionsTable positions={positions} />);
  expect(screen.getByText('$182.50')).toBeInTheDocument();
  expect(screen.getByText('$850.00')).toBeInTheDocument();
});

test('renders opened_at dates', () => {
  render(<PositionsTable positions={positions} />);
  expect(screen.getByText('2026-01-10')).toBeInTheDocument();
  expect(screen.getByText('2026-03-15')).toBeInTheDocument();
});

test('renders empty state when positions is empty', () => {
  render(<PositionsTable positions={[]} />);
  expect(screen.getByText('No open positions')).toBeInTheDocument();
});
