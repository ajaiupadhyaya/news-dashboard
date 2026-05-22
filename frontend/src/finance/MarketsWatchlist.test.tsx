import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/utils';
import { MarketsWatchlist } from './MarketsWatchlist';
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
  { symbol: 'AAPL', price: 212.5, change: 1.8, change_pct: 0.85,
    volume: 50_000_000, as_of: '2026-05-20', sparkline: [1, 2, 3, 4] },
  { symbol: 'NVDA', price: 1200, change: 30, change_pct: 2.5,
    volume: 40_000_000, as_of: '2026-05-20', sparkline: [4, 3, 2, 1] },
];

/** The symbols, in the order they appear in the table body. */
function rowSymbols(): string[] {
  return screen
    .getAllByRole('link')
    .map((a) => a.textContent ?? '')
    .filter((t) => t === 'AAPL' || t === 'NVDA');
}

test('renders a row for each quote, sorted by % change descending', () => {
  renderWithProviders(<MarketsWatchlist quotes={quotes} />);
  // Default sort: % Change, descending - NVDA (2.5%) before AAPL (0.85%).
  expect(rowSymbols()).toEqual(['NVDA', 'AAPL']);
});

test('clicking the Symbol header sorts alphabetically', async () => {
  renderWithProviders(<MarketsWatchlist quotes={quotes} />);
  await userEvent.click(screen.getByRole('button', { name: /Symbol/ }));
  expect(rowSymbols()).toEqual(['AAPL', 'NVDA']);
});

test('adding a symbol calls the add mutation, upper-cased', async () => {
  renderWithProviders(<MarketsWatchlist quotes={quotes} />);
  await userEvent.type(screen.getByLabelText('Add symbol'), 'tsla');
  await userEvent.click(screen.getByRole('button', { name: 'Add' }));
  await waitFor(() => expect(addWatchlist).toHaveBeenCalledWith('TSLA'));
});

test('removing a symbol calls the remove mutation', async () => {
  renderWithProviders(<MarketsWatchlist quotes={quotes} />);
  await userEvent.click(screen.getByLabelText('Remove AAPL'));
  await waitFor(() => expect(removeWatchlist).toHaveBeenCalledWith('AAPL'));
});
