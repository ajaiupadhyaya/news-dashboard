import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { EconomicsPanel } from './EconomicsPanel';

vi.mock('../lib/api', () => ({
  api: {
    economicsOverview: vi.fn().mockResolvedValue({
      indicators: [
        {
          series_id: 'UNRATE', name: 'Unemployment Rate', unit: '%',
          latest: 4.1, latest_date: '2026-04-01', change: -0.1,
          trend: 'in', sparkline: [4.3, 4.2, 4.1],
        },
      ],
      calendar: [{ date: '2026-05-13', release_name: 'Consumer Price Index' }],
      updated_at: '2026-05-21T20:00:00+00:00',
    }),
  },
}));

test('shows a loading skeleton before data arrives', () => {
  renderWithProviders(<EconomicsPanel />);
  expect(screen.getByRole('status')).toBeInTheDocument();
});

test('renders indicator tiles and the release calendar', async () => {
  renderWithProviders(<EconomicsPanel />);
  await waitFor(() =>
    expect(screen.getByText('Unemployment Rate')).toBeInTheDocument(),
  );
  expect(screen.getByText('Consumer Price Index')).toBeInTheDocument();
});
