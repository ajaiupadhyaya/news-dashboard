import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/utils';
import { WatchlistTable } from './WatchlistTable';
import type { WatchlistQuote } from '../lib/types';

const addWatchlist = vi.fn().mockResolvedValue({ symbols: [] });
const removeWatchlist = vi.fn().mockResolvedValue({ symbols: [] });
vi.mock('../lib/api', () => ({
  api: {
    addWatchlist: (s: string) => addWatchlist(s),
    removeWatchlist: (s: string) => removeWatchlist(s),
  },
}));

const quotes: WatchlistQuote[] = [
  {
    symbol: 'AAPL', price: 212.5, change: 1.8, change_pct: 0.85,
    volume: 1, as_of: '2026-05-20', sparkline: [1, 2, 3, 4, 5],
  },
];

test('renders a row for each quote', () => {
  renderWithProviders(<WatchlistTable quotes={quotes} />);
  expect(screen.getByText('AAPL')).toBeInTheDocument();
  expect(screen.getByText('+0.85%')).toBeInTheDocument();
});

test('adding a symbol calls the add mutation, upper-cased', async () => {
  renderWithProviders(<WatchlistTable quotes={quotes} />);
  await userEvent.type(screen.getByLabelText('Add symbol'), 'nvda');
  await userEvent.click(screen.getByRole('button', { name: 'Add' }));
  await waitFor(() => expect(addWatchlist).toHaveBeenCalledWith('NVDA'));
});

test('removing a symbol calls the remove mutation', async () => {
  renderWithProviders(<WatchlistTable quotes={quotes} />);
  await userEvent.click(screen.getByLabelText('Remove AAPL'));
  await waitFor(() => expect(removeWatchlist).toHaveBeenCalledWith('AAPL'));
});
