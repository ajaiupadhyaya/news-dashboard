import { vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { Home } from './Home';

vi.mock('../lib/api', () => ({
  api: {
    overview: vi.fn().mockResolvedValue({
      watchlist: [], indices: [], sectors: [],
      breadth: {
        advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0,
      },
      updated_at: '2026-05-20T20:00:00+00:00',
    }),
    addWatchlist: vi.fn(),
    removeWatchlist: vi.fn(),
    economicsOverview: vi.fn().mockResolvedValue({
      indicators: [], calendar: [], updated_at: '2026-05-20T20:00:00+00:00',
    }),
  },
}));

test('renders the four-quadrant dashboard shell', () => {
  renderWithProviders(<Home />);
  expect(screen.getByText('NMD')).toBeInTheDocument();
  expect(screen.getByText('News')).toBeInTheDocument();
  expect(screen.getByText('Politics')).toBeInTheDocument();
  expect(screen.getByText('Economics')).toBeInTheDocument();
  expect(screen.getByText('Finance')).toBeInTheDocument();
});
