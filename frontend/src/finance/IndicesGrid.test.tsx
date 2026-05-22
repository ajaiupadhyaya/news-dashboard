import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { IndicesGrid } from './IndicesGrid';
import type { WatchlistQuote } from '../lib/types';

const indices: WatchlistQuote[] = [
  { symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.22, volume: 0,
    as_of: '2026-05-20', sparkline: [1, 2, 3, 4] },
  { symbol: '^VIX', price: 14.2, change: -0.3, change_pct: -2.1, volume: 0,
    as_of: '2026-05-20', sparkline: [4, 3, 2, 1] },
];

test('renders each index with a friendly name and a drill-down link', () => {
  renderWithProviders(<IndicesGrid indices={indices} />);
  expect(screen.getByText('S&P 500')).toBeInTheDocument();
  expect(screen.getByText('VIX')).toBeInTheDocument();
  expect(screen.getByText('5,400.00')).toBeInTheDocument();
  expect(screen.getByText('+0.22%')).toBeInTheDocument();
  expect(screen.getByText('-2.10%')).toBeInTheDocument();
  const link = screen.getByRole('link', { name: /S&P 500/ });
  expect(link).toHaveAttribute('href', '/finance/%5EGSPC');
});
