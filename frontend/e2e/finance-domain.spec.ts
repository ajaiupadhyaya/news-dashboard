import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

function makeBars(n: number) {
  const bars = [];
  let price = 180;
  for (let i = 0; i < n; i++) {
    price += Math.sin(i / 7) * 2;
    bars.push({
      date: new Date(Date.UTC(2024, 0, 1 + i)).toISOString().slice(0, 10),
      open: price, high: price + 3, low: price - 3, close: price + 1,
      volume: 1_000_000,
    });
  }
  return bars;
}

const bars = makeBars(120);

const overview = {
  watchlist: [
    {
      symbol: 'AAPL', price: 212.5, change: 1.8, change_pct: 0.85,
      volume: 50_000_000, as_of: '2026-05-20',
      sparkline: [205, 207, 206, 209, 211, 210, 212.5],
    },
  ],
  indices: [
    {
      symbol: '^GSPC', price: 5400, change: 12, change_pct: 0.22,
      volume: 0, as_of: '2026-05-20',
    },
  ],
  sectors: [{ symbol: 'XLK', name: 'Technology', change_pct: 1.1 }],
  breadth: { advancers: 2, decliners: 0, unchanged: 0, advance_decline_ratio: 2 },
  updated_at: '2026-05-20T20:00:00+00:00',
};

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
    { symbol: '^IXIC', price: 17000, change: 60, change_pct: 0.35, volume: 0,
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
    sma_50: bars.map((b) => b.close),
    sma_200: bars.map(() => null),
    rsi: bars.map((_, i) => (i < 14 ? null : 55)),
    macd_line: bars.map((_, i) => (i < 26 ? null : 0.4)),
    macd_signal: bars.map((_, i) => (i < 26 ? null : 0.2)),
    macd_histogram: bars.map((_, i) => (i < 26 ? null : 0.2)),
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

async function stubApi(page: Page) {
  await page.route('**/api/auth/status', (route) =>
    route.fulfill({ json: { auth_enabled: false } }),
  );
  await page.route('**/api/finance/overview', (route) =>
    route.fulfill({ json: overview }),
  );
  await page.route('**/api/finance/markets', (route) =>
    route.fulfill({ json: markets }),
  );
  await page.route('**/api/finance/instrument/**', (route) =>
    route.fulfill({ json: instrument }),
  );
}

test('home links into the Finance domain page and drills down', async ({
  page,
}) => {
  await stubApi(page);
  await page.goto('/');

  // The Finance panel header links to the domain page.
  await page.getByRole('link', { name: 'Open Finance' }).click();
  await expect(page).toHaveURL(/\/finance$/);

  // The bento tiles render.
  await expect(page.getByText('Asset Classes')).toBeVisible();
  await expect(page.getByText('Top Movers')).toBeVisible();
  await expect(page.getByText('Watchlist')).toBeVisible();
  await expect(page.getByRole('group', { name: 'Index' })).toBeVisible();

  // Switching the hero index works.
  await page.getByRole('button', { name: 'Nasdaq' }).click();
  await expect(page.getByRole('button', { name: 'Nasdaq' })).toHaveAttribute(
    'aria-pressed', 'true',
  );

  // A top mover drills down to its instrument page.
  await page.getByRole('link', { name: /NVDA/ }).click();
  await expect(page).toHaveURL(/\/finance\/NVDA$/);
  // The instrument stub returns the AAPL fixture for every symbol.
  await expect(page.getByRole('heading', { name: 'AAPL' })).toBeVisible();
});
