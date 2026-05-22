import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test/utils';
import { InstrumentRoute } from './InstrumentRoute';

const bars = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
  open: 100 + i, high: 104 + i, low: 98 + i, close: 102 + i, volume: 1000,
}));

const instrument = {
  symbol: 'AAPL',
  profile: {
    symbol: 'AAPL', name: 'Apple Inc.', sector: 'Technology',
    industry: 'Consumer Electronics', market_cap: 3.21e12, pe_ratio: 29.4,
    price_to_book: 48.1, dividend_yield: 0.5, week52_high: 240,
    week52_low: 160, beta: 1.2,
  },
  bars,
  technicals: {
    sma_20: bars.map((b) => b.close),
    sma_50: bars.map(() => null),
    sma_200: bars.map(() => null),
    rsi: bars.map((_, i) => (i < 14 ? null : 55)),
    macd_line: bars.map((_, i) => (i < 25 ? null : 0.4)),
    macd_signal: bars.map((_, i) => (i < 25 ? null : 0.2)),
    macd_histogram: bars.map((_, i) => (i < 25 ? null : 0.2)),
    bb_upper: bars.map((b) => b.close + 5),
    bb_middle: bars.map((b) => b.close),
    bb_lower: bars.map((b) => b.close - 5),
    volume: bars.map(() => 1000),
  },
  stats: {
    momentum_1m: 4.2, momentum_3m: 9.1, momentum_6m: 15.3,
    volatility_30d: 22.5, week52_high: 240, week52_low: 160,
  },
  returns: {
    week_1: 1.2, month_1: -3.4, month_3: 8.0, month_6: 12.5,
    ytd: 6.1, year_1: 22.0, year_3: null,
  },
  updated_at: '2026-05-20T20:00:00+00:00',
};

const instrumentFn = vi.fn();
vi.mock('../lib/api', () => ({
  api: { instrument: (s: string, r?: string) => instrumentFn(s, r) },
}));

test('renders the enriched drill-down for a symbol', async () => {
  instrumentFn.mockResolvedValue(instrument);
  renderWithProviders(<InstrumentRoute />, {
    route: '/finance/AAPL',
    path: '/finance/:symbol',
  });
  await waitFor(() =>
    expect(screen.getByRole('heading', { name: 'AAPL' })).toBeInTheDocument(),
  );
  expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
  expect(screen.getByText('Fundamentals')).toBeInTheDocument();
  expect(screen.getByText('Returns')).toBeInTheDocument();
  expect(screen.getByText('RSI (14)')).toBeInTheDocument();
  expect(screen.getByText('MACD')).toBeInTheDocument();
  expect(screen.getByRole('group', { name: 'Timeframe' })).toBeInTheDocument();
});

test('shows an error message when the instrument has no data', async () => {
  instrumentFn.mockRejectedValue(new Error('404'));
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
