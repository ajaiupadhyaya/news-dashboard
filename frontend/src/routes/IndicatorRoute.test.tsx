import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { IndicatorRoute } from './IndicatorRoute';

vi.mock('../lib/api', () => ({
  api: {
    indicator: vi.fn().mockResolvedValue({
      series_id: 'UNRATE', name: 'Unemployment Rate', unit: '%',
      series: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
        value: 4 + Math.sin(i / 5) * 0.5,
      })),
      latest: 4.1, change: -0.1, yoy: 0.3, range_low: 3.4, range_high: 4.3,
      momentum: -2.4,
      recession_signals: [
        {
          name: 'Yield curve (10y-2y)', value: -0.15, status: 'alert',
          detail: 'Inverted — historically a recession precursor.',
        },
      ],
      updated_at: '2026-05-21T20:00:00+00:00',
    }),
  },
}));

test('renders the indicator drill-down', async () => {
  renderWithProviders(<IndicatorRoute />, {
    route: '/economics/UNRATE',
    path: '/economics/:seriesId',
  });
  await waitFor(() =>
    expect(
      screen.getByRole('heading', { name: 'Unemployment Rate' }),
    ).toBeInTheDocument(),
  );
  expect(screen.getByText('Recession Signals')).toBeInTheDocument();
  expect(screen.getByText('Yield curve (10y-2y)')).toBeInTheDocument();
});
