import { vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

vi.mock('./lib/api', () => ({
  setAuthToken: vi.fn(),
  api: {
    authStatus: vi.fn().mockResolvedValue({ auth_enabled: false }),
    overview: vi.fn().mockResolvedValue({
      watchlist: [], indices: [], sectors: [],
      breadth: {
        advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0,
      },
      updated_at: '2026-05-20T20:00:00+00:00',
    }),
    addWatchlist: vi.fn(),
    removeWatchlist: vi.fn(),
  },
}));

test('renders the dashboard once the auth status resolves', async () => {
  render(<App />);
  await waitFor(() =>
    expect(screen.getByText('NMD')).toBeInTheDocument(),
  );
});
