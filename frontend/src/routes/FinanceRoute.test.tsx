import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { FinanceRoute } from './FinanceRoute';

const bars = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
  open: 100 + i, high: 104 + i, low: 98 + i, close: 102 + i, volume: 1000,
}));

const markets = {
  asset_classes: [
    { label: 'Equities', symbol: '^GSPC', price: 5400, change_pct: 0.4,
      sparkline: [1, 2, 3, 4] },
    { label: 'Crypto', symbol: 'BTC-USD', price: 68000, change_pct: -1.2,
      sparkline: [4, 3, 2, 1] },
  ],
  indices: [
    { symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.22, volume: 0,
      as_of: '2026-05-20', sparkline: [1, 2, 3, 4] },
    { symbol: '^VIX', price: 14.2, change: -0.3, change_pct: -2.1, volume: 0,
      as_of: '2026-05-20', sparkline: [4, 3, 2, 1] },
  ],
  gainers: [{ symbol: 'NVDA', price: 1200, change_pct: 3.4 }],
  losers: [{ symbol: 'INTC', price: 30, change_pct: -2.8 }],
  sectors: [{ symbol: 'XLK', name: 'Technology', change_pct: 1.1 }],
  breadth: { advancers: 6, decliners: 4, unchanged: 0, advance_decline_ratio: 1.5 },
  updated_at: '2026-05-21T20:00:00+00:00',
};

const overview = {
  watchlist: [
    { symbol: 'AAPL', price: 212.5, change: 1.8, change_pct: 0.85,
      volume: 50_000_000, as_of: '2026-05-20', sparkline: [1, 2, 3, 4] },
  ],
  indices: [],
  sectors: [],
  breadth: { advancers: 0, decliners: 0, unchanged: 0, advance_decline_ratio: 0 },
  updated_at: '2026-05-21T20:00:00+00:00',
};

const instrument = {
  symbol: '^GSPC',
  profile: { symbol: '^GSPC', name: 'S&P 500' },
  bars,
  technicals: {
    sma_20: bars.map(() => null), sma_50: bars.map(() => null),
    sma_200: bars.map(() => null), rsi: [], macd_line: [], macd_signal: [],
    macd_histogram: [], bb_upper: [], bb_middle: [], bb_lower: [],
    volume: bars.map(() => 1000),
  },
  stats: {
    momentum_1m: 0, momentum_3m: 0, momentum_6m: 0, volatility_30d: 0,
    week52_high: null, week52_low: null,
  },
  returns: {
    week_1: null, month_1: null, month_3: null, month_6: null, ytd: null,
    year_1: null, year_3: null,
  },
  updated_at: '2026-05-20T20:00:00+00:00',
};

const marketsFn = vi.fn();
const overviewFn = vi.fn();
const instrumentFn = vi.fn();

vi.mock('../lib/api', () => ({
  api: {
    markets: () => marketsFn(),
    overview: () => overviewFn(),
    instrument: (s: string, r?: string) => instrumentFn(s, r),
    addWatchlist: vi.fn(),
    removeWatchlist: vi.fn(),
  },
}));

test('renders the bento grid of market tiles', async () => {
  marketsFn.mockResolvedValue(markets);
  overviewFn.mockResolvedValue(overview);
  instrumentFn.mockResolvedValue(instrument);
  renderWithProviders(<FinanceRoute />, { route: '/finance', path: '/finance' });
  await waitFor(() =>
    expect(screen.getByText('Asset Classes')).toBeInTheDocument(),
  );
  expect(screen.getByText('Market Chart')).toBeInTheDocument();
  expect(screen.getByText('Top Movers')).toBeInTheDocument();
  expect(screen.getByText('Watchlist')).toBeInTheDocument();
  // Data from the tiles.
  expect(screen.getByText('Equities')).toBeInTheDocument();
  expect(screen.getByText('NVDA')).toBeInTheDocument();
  await waitFor(() =>
    expect(screen.getByText('AAPL')).toBeInTheDocument(),
  );
});

test('shows an error message when the markets payload fails', async () => {
  marketsFn.mockRejectedValueOnce(new Error('boom'));
  overviewFn.mockResolvedValue(overview);
  renderWithProviders(<FinanceRoute />, { route: '/finance', path: '/finance' });
  await waitFor(() =>
    expect(screen.getByText(/Couldn't load market data/)).toBeInTheDocument(),
  );
});
