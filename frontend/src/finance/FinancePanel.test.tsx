import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { FinancePanel } from './FinancePanel';

vi.mock('../lib/api', () => ({
  api: {
    overview: vi.fn().mockResolvedValue({
      watchlist: [
        {
          symbol: 'AAPL', price: 212.5, change: 1.8, change_pct: 0.85,
          volume: 1, as_of: '2026-05-20', sparkline: [1, 2, 3, 4],
        },
      ],
      indices: [
        {
          symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.22,
          volume: 0, as_of: '2026-05-20',
        },
      ],
      sectors: [{ symbol: 'XLK', name: 'Technology', change_pct: 1.1 }],
      breadth: {
        advancers: 2, decliners: 1, unchanged: 0, advance_decline_ratio: 2,
      },
      updated_at: '2026-05-20T20:00:00+00:00',
    }),
    addWatchlist: vi.fn(),
    removeWatchlist: vi.fn(),
  },
}));

test('shows a loading skeleton before data arrives', () => {
  renderWithProviders(<FinancePanel />);
  expect(screen.getByRole('status')).toBeInTheDocument();
});

test('renders watchlist, indices, sectors, and breadth once loaded', async () => {
  renderWithProviders(<FinancePanel />);
  await waitFor(() =>
    expect(screen.getByText('AAPL')).toBeInTheDocument(),
  );
  expect(screen.getByText('S&P')).toBeInTheDocument();
  expect(screen.getByText('XLK')).toBeInTheDocument();
  expect(screen.getByText(/2 adv/)).toBeInTheDocument();
});
