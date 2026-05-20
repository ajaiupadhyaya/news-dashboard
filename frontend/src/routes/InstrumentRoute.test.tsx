import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { InstrumentRoute } from './InstrumentRoute';

const instrument = {
  symbol: 'AAPL',
  profile: {
    symbol: 'AAPL', name: 'Apple Inc.', sector: 'Technology',
    industry: 'Consumer Electronics', market_cap: 3.21e12, pe_ratio: 29.4,
    price_to_book: 48.1, dividend_yield: 0.5, week52_high: 240,
    week52_low: 160, beta: 1.2,
  },
  bars: [
    { date: '2026-01-02', open: 100, high: 104, low: 98, close: 102, volume: 1 },
    { date: '2026-01-03', open: 102, high: 106, low: 101, close: 105, volume: 1 },
  ],
  technicals: {
    sma_20: [null, null], sma_50: [null, null], sma_200: [null, null],
  },
  stats: {
    momentum_1m: 4.2, momentum_3m: 9.1, momentum_6m: 15.3,
    volatility_30d: 22.5, week52_high: 240, week52_low: 160,
  },
  updated_at: '2026-05-20T20:00:00+00:00',
};

const instrumentFn = vi.fn();
vi.mock('../lib/api', () => ({
  api: { instrument: (s: string) => instrumentFn(s) },
}));

test('renders the drill-down page for a symbol', async () => {
  instrumentFn.mockResolvedValueOnce(instrument);
  renderWithProviders(<InstrumentRoute />, {
    route: '/finance/AAPL',
    path: '/finance/:symbol',
  });
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: 'AAPL' })).toBeInTheDocument(),
  );
  expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
  expect(screen.getByText('Fundamentals')).toBeInTheDocument();
  expect(screen.getByText('SMA 20')).toBeInTheDocument();
});

test('shows an error message when the instrument has no data', async () => {
  instrumentFn.mockRejectedValueOnce(new Error('404'));
  renderWithProviders(<InstrumentRoute />, {
    route: '/finance/ZZZZ',
    path: '/finance/:symbol',
  });
  await waitFor(() =>
    expect(
      screen.getByText(/No data available for ZZZZ/),
    ).toBeInTheDocument(),
  );
});
