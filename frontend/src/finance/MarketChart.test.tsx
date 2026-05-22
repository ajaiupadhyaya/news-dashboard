import { vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test/utils';
import { MarketChart } from './MarketChart';
import type { WatchlistQuote } from '../lib/types';

const bars = Array.from({ length: 30 }, (_, i) => ({
  date: new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
  open: 100 + i, high: 104 + i, low: 98 + i, close: 102 + i, volume: 1000,
}));

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

const instrumentFn = vi.fn();
vi.mock('../lib/api', () => ({
  api: { instrument: (s: string, r?: string) => instrumentFn(s, r) },
}));

const indices: WatchlistQuote[] = [
  { symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.2, volume: 0,
    as_of: '2026-05-20', sparkline: [1, 2, 3] },
  { symbol: '^IXIC', price: 17000, change: 60, change_pct: 0.3, volume: 0,
    as_of: '2026-05-20', sparkline: [1, 2, 3] },
];

test('renders the index switcher and the chart controls', async () => {
  instrumentFn.mockResolvedValue(instrument);
  renderWithProviders(<MarketChart indices={indices} />);
  expect(screen.getByRole('group', { name: 'Index' })).toBeInTheDocument();
  expect(screen.getByRole('group', { name: 'Timeframe' })).toBeInTheDocument();
  expect(screen.getByRole('group', { name: 'Chart type' })).toBeInTheDocument();
  await waitFor(() => expect(instrumentFn).toHaveBeenCalledWith('^GSPC', '1y'));
});

test('switching the index refetches for the new symbol', async () => {
  instrumentFn.mockResolvedValue(instrument);
  renderWithProviders(<MarketChart indices={indices} />);
  await userEvent.click(screen.getByRole('button', { name: 'Nasdaq' }));
  await waitFor(() => expect(instrumentFn).toHaveBeenCalledWith('^IXIC', '1y'));
});
